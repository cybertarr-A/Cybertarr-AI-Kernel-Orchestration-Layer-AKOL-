#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h> // IWYU pragma: keep
#include <pthread.h>
#include <stdlib.h>
#include <linux/types.h>
#include <bpf/libbpf.h>
#include "daemon.h"

static int exiting = 0;

static void sig_handler(int signo) {
    exiting = 1;
}

static void handle_event(void *ctx, int cpu, void *data, __u32 data_sz) {
    if (data_sz < sizeof(struct spike_event)) return;
    const struct spike_event *e = data;
    process_spike_event(e);
}

static void *watchdog_thread(void *arg) {
    while (!exiting) {
        double loadavg;
        if (getloadavg(&loadavg, 1) != -1) {
            if (loadavg > 4.0) {
                if (!ai_failsafe_active) {
                    printf("[WATCHDOG] SYSTEM LOAD CRITICAL (%.2f). Disabling AI boundaries.\n", loadavg);
                    ai_failsafe_active = 1;
                }
            } else if (loadavg < 3.0) {
                if (ai_failsafe_active) {
                    printf("[WATCHDOG] SYSTEM LOAD NORMAL (%.2f). Restoring AI control.\n", loadavg);
                    ai_failsafe_active = 0;
                }
            }
        }
        sleep(5);
    }
    return NULL;
}

int main(int argc, char **argv) {
    struct bpf_object *obj;
    struct bpf_program *prog;
    struct bpf_link *link_switch = NULL;
    struct bpf_map *spikes_map;
    struct perf_buffer *pb = NULL;
    int err;

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    init_scheduler();
    init_controller();

    // Load BPF object
    obj = bpf_object__open_file("../ebpf/spike_kern.o", NULL);
    if (libbpf_get_error(obj)) {
        fprintf(stderr, "ERROR: opening BPF object file failed\n");
        return 1;
    }

    // Load programs into kernel
    err = bpf_object__load(obj);
    if (err) {
        fprintf(stderr, "ERROR: loading BPF object file failed\n");
        return 1;
    }

    // Attach tracepoint
    prog = bpf_object__find_program_by_name(obj, "handle_sched_switch");
    if (!prog) {
        fprintf(stderr, "ERROR: finding BPF program failed\n");
        return 1;
    }

    link_switch = bpf_program__attach(prog);
    if (libbpf_get_error(link_switch)) {
        fprintf(stderr, "ERROR: attaching BPF program failed\n");
        return 1;
    }

    // Setup perf buffer
    spikes_map = bpf_object__find_map_by_name(obj, "spikes");
    int map_fd = bpf_map__fd(spikes_map);
    
    pb = perf_buffer__new(map_fd, 8, handle_event, NULL, NULL, NULL);
    err = libbpf_get_error(pb);
    if (err) {
        fprintf(stderr, "ERROR: setting up perf buffer failed\n");
        return 1;
    }

    pthread_t watchdog_tid;
    pthread_create(&watchdog_tid, NULL, watchdog_thread, NULL);

    printf("[DAEMON] Cybertarr AKOL Real-Time Loop Started.\n");

    while (!exiting) {
        err = perf_buffer__poll(pb, 100);
        if (err < 0 && err != -EINTR) {
            fprintf(stderr, "Error polling perf buffer: %d\n", err);
            break;
        }
    }

    printf("[DAEMON] Exiting gracefully...\n");
    pthread_join(watchdog_tid, NULL);
    perf_buffer__free(pb);
    bpf_link__destroy(link_switch);
    bpf_object__close(obj);
    cleanup_controller();

    return 0;
}
