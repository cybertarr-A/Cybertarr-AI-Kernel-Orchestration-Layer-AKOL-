#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sched.h>
#include <fcntl.h>
#include "daemon.h"

#define CGROUP_DIR "/sys/fs/cgroup/cybertarr"

// Whitelist of critical processes that should never be throttled
const char *whitelist[] = {
    "systemd", "kworker", "sshd", "zsh", "bash", "tmux", NULL
};

int is_whitelisted(const char *comm) {
    for (int i = 0; whitelist[i] != NULL; i++) {
        if (strstr(comm, whitelist[i]) != NULL) {
            return 1;
        }
    }
    return 0;
}

void init_scheduler() {
    struct stat st = {0};
    if (stat(CGROUP_DIR, &st) == -1) {
        if (mkdir(CGROUP_DIR, 0700) != 0) {
            perror("Failed to create Cybertarr cgroup");
            return;
        }
    }
    
    char cpu_max_path[256];
    snprintf(cpu_max_path, sizeof(cpu_max_path), "%s/cpu.max", CGROUP_DIR);
    int fd = open(cpu_max_path, O_WRONLY);
    if (fd != -1) {
        write(fd, "20000 100000\n", 13);
        close(fd);
    }
}

void isolate_core(int pid) {
    long num_cores = sysconf(_SC_NPROCESSORS_ONLN);
    if (num_cores <= 1) return; 
    
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(num_cores - 1, &cpuset); 
    
    sched_setaffinity(pid, sizeof(cpu_set_t), &cpuset);
}

void apply_scheduler_actions(int pid, const char *comm, double adjustment) {
    if (is_whitelisted(comm)) {
        return; 
    }

    if (adjustment < -0.5) { 
        if (setpriority(PRIO_PROCESS, pid, 19) == -1) return; 

        isolate_core(pid);

        char procs_path[256];
        snprintf(procs_path, sizeof(procs_path), "%s/cgroup.procs", CGROUP_DIR);
        int fd = open(procs_path, O_WRONLY | O_APPEND);
        if (fd != -1) {
            char pid_str[32];
            int len = snprintf(pid_str, sizeof(pid_str), "%d\n", pid);
            write(fd, pid_str, len);
            close(fd);
            printf("[SCHEDULER] RL+PID THROTTLED aggressive spike PID %d (%s) - Adj: %.2f\n", pid, comm, adjustment);
        }
    } else if (adjustment > 0.5) { 
        setpriority(PRIO_PROCESS, pid, -5);
        int fd = open("/sys/fs/cgroup/cgroup.procs", O_WRONLY | O_APPEND);
        if (fd != -1) {
            char pid_str[32];
            int len = snprintf(pid_str, sizeof(pid_str), "%d\n", pid);
            write(fd, pid_str, len);
            close(fd);
        }
    } else {
        setpriority(PRIO_PROCESS, pid, 0);
    }
}
