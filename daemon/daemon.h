#ifndef __DAEMON_H
#define __DAEMON_H

#include "../ebpf/cybertarr_common.h"

extern int ai_failsafe_active;

// Initialize the controller
void init_controller();

// Clean up controller resources
void cleanup_controller();

// Process an incoming spike event
void process_spike_event(const struct spike_event *event);

// Throttle or boost a process based on an AI score (0.0 to 1.0, 1.0 being worst spike)
void apply_scheduler_actions(int pid, const char *comm, double score);

// Init cgroups manager
void init_scheduler();

#endif /* __DAEMON_H */
