# Cybertarr AI Kernel Orchestration Layer (AKOL)

An intelligent layer acting on top of Linux to dynamically observe CPU behavior via eBPF, detect spikes, and orchestrate CPU allocation using cgroups and priority logic driven by a contextual AI predictive model.

## Features

- **eBPF Real-Time Tracking**: Hooks into `sched_switch` natively without heavy modules.
- **Micro-Spike Detection**: Captures elapsed duration deltas under 20ms.
- **Python ML Inference**: Uses historical probability scoring (variance + thresholds) delivered via zero-latency Unix Domain Sockets to the Native C Daemon.
- **Priority Scaling**: Limits processes dynamically via `cgroups cpu.max` or adjusts nice values via `setpriority()`.
- **FastAPI Real-Time Web Dashboard**: A red/black cyberpunk UI connected via Server-Sent Events showing instantaneous workload.

## System Prerequisites

This project uses native libbpf, clang, and Python 3. 

1. Install dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install -y clang llvm libbpf-dev linux-headers-$(uname -r) make python3 python3-pip python3-venv
   ```
2. Enable cgroup v2 on your system if not already active:
   Make sure `/sys/fs/cgroup/cgroup.procs` exists.

## Build Instructions

1. Navigate to the project root:
   ```bash
   cd cybertarr-akol
   ```
2. Run the build script to compile the Kernel and Daemon modules as well as provision the Python env:
   ```bash
   ./scripts/build.sh
   ```

## Run Instructions

You can run the daemon interactively or via Systemd. **Root is required** for eBPF attachment and cgroup manipulation.

### Option A: Interactive Run
```bash
sudo ./scripts/run.sh
```

### Option B: Systemd Installation
```bash
sudo cp systemd/cybertarr.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cybertarr
```

## Viewing the Dashboard

Once running, the FastAPI service runs a web interface accessible via:
**`http://localhost:8000`**

Enjoy your newly AI-orchestrated Linux system.
