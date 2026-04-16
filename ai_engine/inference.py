import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine.model import ProcessClassifier
from ai_engine.rl_scheduler import RLScheduler
from ai_engine.signals import TelemetryGatherer

AI_SOCKET_PATH = "/tmp/akol_ai.sock"

class AIInferenceServer:
    def __init__(self, event_queue: asyncio.Queue):
        self.classifier = ProcessClassifier()
        self.rl_agent = RLScheduler()
        self.telemetry = TelemetryGatherer()
        self.event_queue = event_queue
        
        # State tracking for RL learning
        self.last_states = {} 
        
    async def handle_client(self, reader, writer):
        while True:
            data = await reader.read(128)
            if not data:
                break
                
            try:
                decoded = data.decode('utf-8').strip()
                if not decoded:
                    continue
                parts = decoded.split(',')
                if len(parts) == 2:
                    pid = int(parts[0])
                    duration_ns = float(parts[1])
                    
                    sys_state = self.telemetry.get_system_state()
                    proc_state = self.telemetry.get_process_state(pid)
                    
                    comm = "unknown"
                    try:
                        with open(f'/proc/{pid}/comm', 'r') as f:
                            comm = f.read().strip()
                    except:
                        pass
                        
                    p_class = self.classifier.classify(comm, proc_state['ctx_vol'], proc_state['ctx_invol'], duration_ns)
                    
                    state = {
                        'cpu_usage': sys_state['cpu_usage'],
                        'mem_pressure': sys_state['mem_pressure'],
                        'io_wait': sys_state['io_wait'],
                        'cpu_freq': sys_state['cpu_freq'],
                        'process_class': p_class
                    }
                    
                    action = self.rl_agent.choose_action(state)
                    target_score = self.rl_agent.action_to_target_score(action)
                    
                    if pid in self.last_states:
                        prev_state, prev_action = self.last_states[pid]
                        # Reward: 1.0 - burst length penalty. Add stability points
                        burst_penalty = min(duration_ns / 50000000.0, 1.0)
                        stability_bonus = 0.5 if sys_state['cpu_usage'] < 0.8 else 0.0
                        reward = (1.0 - burst_penalty) + stability_bonus
                        
                        self.rl_agent.learn(prev_state, prev_action, reward, state)
                        
                    self.last_states[pid] = (state, action)
                    
                    writer.write(f"{target_score:.2f}\n".encode('utf-8'))
                    await writer.drain()
                    
                    if not self.event_queue.full():
                        self.event_queue.put_nowait({
                            "pid": pid, 
                            "comm": comm,
                            "duration_ns": duration_ns, 
                            "target_score": target_score,
                            "action": self.rl_agent.action_name(action),
                            "class": p_class,
                            "system_load": sys_state['cpu_usage']
                        })
                        
            except Exception as e:
                pass 
                
        writer.close()

async def backup_model_loop(agent: RLScheduler):
    while True:
        await asyncio.sleep(60) 
        agent.save_model()

async def start_inference_server(event_queue: asyncio.Queue):
    if os.path.exists(AI_SOCKET_PATH):
        os.remove(AI_SOCKET_PATH)
        
    server_instance = AIInferenceServer(event_queue)
    server = await asyncio.start_unix_server(
        server_instance.handle_client,
        path=AI_SOCKET_PATH
    )
    
    os.chmod(AI_SOCKET_PATH, 0o777)
    
    asyncio.create_task(backup_model_loop(server_instance.rl_agent))
    
    async with server:
        await server.serve_forever()
