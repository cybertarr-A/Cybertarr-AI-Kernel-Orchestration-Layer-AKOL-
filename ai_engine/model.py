import os

class ProcessClassifier:
    def __init__(self):
        self.system_critical = {"systemd", "kworker", "sshd", "dbus-daemon", "networkd", "rcu_sched", "su", "sudo", "migration", "irq"}
        self.interactive = {"xorg", "gnome-shell", "plasma", "kwin", "bash", "zsh", "firefox", "chrome", "tmux", "code"}
        
    def classify(self, comm: str, ctx_vol: int, ctx_invol: int, duration_ns: float) -> str:
        comm_lower = comm.lower()
        for s in self.system_critical:
            if s in comm_lower:
                return "System Critical"
                
        for i in self.interactive:
            if i in comm_lower:
                return "Interactive"
                
        # Heuristics based on context switches
        # Interactive tasks yield voluntarily while waiting for IO/User
        if ctx_vol > 500 and ctx_invol < 100:
            return "Interactive"
            
        # Compute heavy tasks are forcefully preempted
        if duration_ns > 50000000 and ctx_invol > ctx_vol + 10:
            return "Compute Heavy"
            
        return "Background"

