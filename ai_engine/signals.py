import os
import time

class TelemetryGatherer:
    def __init__(self):
        self.last_cpu_times = self._parse_proc_stat()
        self.last_time = time.time()

    def _parse_proc_stat(self):
        try:
            with open('/proc/stat', 'r') as f:
                lines = f.readlines()
                cpu_line = lines[0].split()
                if cpu_line[0] == 'cpu':
                    return [float(x) for x in cpu_line[1:]]
        except Exception:
            pass
        return [0.0] * 10

    def _parse_meminfo(self):
        # Extract MemTotal and MemAvailable
        mem_total = 1.0
        mem_avail = 1.0
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_total = float(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        mem_avail = float(line.split()[1])
        except Exception:
            pass
        # Return memory pressure (0.0 to 1.0)
        return max(0.0, min(1.0 - (mem_avail / mem_total), 1.0))

    def _get_cpu_freq(self):
        # Average across cores
        freqs = []
        try:
            for d in os.listdir('/sys/devices/system/cpu/'):
                if d.startswith('cpu') and d[3:].isdigit():
                    freq_file = f'/sys/devices/system/cpu/{d}/cpufreq/scaling_cur_freq'
                    max_freq_file = f'/sys/devices/system/cpu/{d}/cpufreq/cpuinfo_max_freq'
                    if os.path.exists(freq_file) and os.path.exists(max_freq_file):
                        with open(freq_file, 'r') as f, open(max_freq_file, 'r') as m:
                            cur = float(f.read().strip())
                            mx = float(m.read().strip())
                            freqs.append(cur / mx)
        except Exception:
            pass
        
        return sum(freqs) / len(freqs) if freqs else 0.5

    def get_system_state(self):
        current_cpu_times = self._parse_proc_stat()
        current_time = time.time()
        
        # Calculate deltas for iowait and generic cpu usage
        # cpu times: [user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice]
        
        delta = [c - p for c, p in zip(current_cpu_times, self.last_cpu_times)]
        total_delta = sum(delta) + 1e-5
        
        # Standard CPU usage = 1.0 - (idle_delta / total_delta)
        idle_delta = delta[3]
        cpu_usage = max(0.0, min(1.0 - (idle_delta / total_delta), 1.0))
        
        # IO wait
        iowait_delta = delta[4]
        io_wait = max(0.0, min(iowait_delta / total_delta, 1.0))
        
        self.last_cpu_times = current_cpu_times
        self.last_time = current_time

        mem_pressure = self._parse_meminfo()
        cpu_freq = self._get_cpu_freq()

        return {
            'cpu_usage': cpu_usage,
            'mem_pressure': mem_pressure,
            'io_wait': io_wait,
            'cpu_freq': cpu_freq
        }

    def get_process_state(self, pid):
        # Reads context switches from /proc/<pid>/status
        vol = 0
        invol = 0
        try:
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('voluntary_ctxt_switches:'):
                        vol = int(line.split()[1])
                    elif line.startswith('nonvoluntary_ctxt_switches:'):
                        invol = int(line.split()[1])
        except Exception:
            pass
        return {'ctx_vol': vol, 'ctx_invol': invol}
