#include <linux/types.h>
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include "cybertarr_common.h"

/* Tracepoint format for sched_switch */
struct trace_event_raw_sched_switch {
  unsigned short common_type;
  unsigned char common_flags;
  unsigned char common_preempt_count;
  int common_pid;

  char prev_comm[16];
  __u32 prev_pid;
  int prev_prio;
  long prev_state;

  char next_comm[16];
  __u32 next_pid;
  int next_prio;
};

/* Map to track process start times (TGID/PID as key) */
struct {
  __uint(type, BPF_MAP_TYPE_HASH);
  __uint(max_entries, 10240);
  __type(key, __u32);
  __type(value, __u64);
} start_times SEC(".maps");

/* Map to push spike events to userspace */
struct {
  __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
  __uint(key_size, sizeof(__u32));
  __uint(value_size, sizeof(__u32));
} spikes SEC(".maps");

/* 20 milliseconds default threshold for spikes.
   Can be overridden by loading userspace program, but kept static here for
   simplicity.
*/
#define MIN_SPIKE_NS 20000000ULL

SEC("tracepoint/sched/sched_switch")
int handle_sched_switch(struct trace_event_raw_sched_switch *ctx) {
  __u64 ts = bpf_ktime_get_ns();
  __u32 prev_pid = ctx->prev_pid;
  __u32 next_pid = ctx->next_pid;

  // Process being scheduled OUT (prev)
  // We calculate how long it ran by looking up its start time
  __u64 *start_ts = bpf_map_lookup_elem(&start_times, &prev_pid);
  if (start_ts) {
    __u64 delta = ts - *start_ts;

    // If the process ran longer than the micro-spike threshold, push an event
    if (delta > MIN_SPIKE_NS) {
      struct spike_event event = {};
      event.pid = prev_pid;
      event.tgid =
          bpf_get_current_pid_tgid() >>
          32; // Not totally accurate from tracepoint ctx but good enough
      event.duration_ns = delta;
      bpf_probe_read_kernel_str(&event.comm, sizeof(event.comm),
                                ctx->prev_comm);

      bpf_perf_event_output(ctx, &spikes, BPF_F_CURRENT_CPU, &event,
                            sizeof(event));
    }
    // Remove start time to keep map clean
    bpf_map_delete_elem(&start_times, &prev_pid);
  }

  // Process being scheduled IN (next)
  // We record its start time so we can measure on the next sched_switch out
  bpf_map_update_elem(&start_times, &next_pid, &ts, BPF_ANY);

  return 0;
}

char LICENSE[] SEC("license") = "Dual BSD/GPL";
