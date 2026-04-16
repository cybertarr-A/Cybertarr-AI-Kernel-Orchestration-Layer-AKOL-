#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <time.h>
#include "daemon.h"

#define AI_SOCKET_PATH "/tmp/akol_ai.sock"
#define MAX_PIDS 32768

static int ai_sock = -1;
int ai_failsafe_active = 0; // Extern controlled by watchdog

// PID Controller parameters
static double Kp = 0.5;
static double Ki = 0.1;
static double Kd = 0.2;

struct pid_state {
    double integral;
    double prev_error;
    long last_ts_ms;
};

static struct pid_state states[MAX_PIDS];

long get_current_time_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

void init_controller() {
    memset(states, 0, sizeof(states));
    ai_sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (ai_sock < 0) {
        perror("Failed to create AI socket");
        return;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, AI_SOCKET_PATH, sizeof(addr.sun_path) - 1);

    if (connect(ai_sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(ai_sock);
        ai_sock = -1;
    } else {
        printf("[CONTROLLER] Connected to AI engine via UDS.\n");
    }
}

void cleanup_controller() {
    if (ai_sock >= 0) close(ai_sock);
}

void process_spike_event(const struct spike_event *event) {
    double target_score = 0.5; 
    
    if (ai_failsafe_active) {
        target_score = 1.0; // Assume bad during emergency
    } else {
        if (ai_sock < 0) {
            init_controller();
        }

        if (ai_sock >= 0) {
            char req[128];
            snprintf(req, sizeof(req), "%d,%llu\n", event->pid, event->duration_ns);
            if (write(ai_sock, req, strlen(req)) < 0) {
                close(ai_sock);
                ai_sock = -1;
            } else {
                char res[32];
                int n = read(ai_sock, res, sizeof(res) - 1);
                if (n > 0) {
                    res[n] = '\0';
                    target_score = atof(res); // AI outputs desired load score
                }
            }
        }
    }

    // PID Closed-Loop Calculation
    int idx = event->pid % MAX_PIDS;
    long current_ts = get_current_time_ms();
    
    double dt = (current_ts - states[idx].last_ts_ms) / 1000.0;
    if (dt <= 0.0) dt = 0.001; 
    
    double actual_load = (double)event->duration_ns / 20000000.0;
    if(actual_load > 1.0) actual_load = 1.0;
    
    double error = target_score - actual_load;
    
    states[idx].integral += error * dt;
    if(states[idx].integral > 10.0) states[idx].integral = 10.0;
    if(states[idx].integral < -10.0) states[idx].integral = -10.0;
    
    double derivative = (error - states[idx].prev_error) / dt;
    double adjustment = (Kp * error) + (Ki * states[idx].integral) + (Kd * derivative);
    
    states[idx].prev_error = error;
    states[idx].last_ts_ms = current_ts;

    apply_scheduler_actions(event->pid, event->comm, adjustment);
}
