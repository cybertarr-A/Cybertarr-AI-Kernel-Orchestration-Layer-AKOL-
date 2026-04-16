#ifndef __CYBERTARR_COMMON_H
#define __CYBERTARR_COMMON_H

#define TASK_COMM_LEN 16

/* Event fired when a thread gets scheduled out after a high CPU burst */
struct spike_event {
    unsigned int pid;
    unsigned int tgid;
    unsigned long long duration_ns;
    char comm[TASK_COMM_LEN];
};

#endif /* __CYBERTARR_COMMON_H */
