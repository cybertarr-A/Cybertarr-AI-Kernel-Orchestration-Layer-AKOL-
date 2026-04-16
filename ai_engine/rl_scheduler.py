import numpy as np
import yaml
import os

class RLScheduler:
    def __init__(self):
        # State: [cpu_usage, mem_pressure, io_wait, class_id]
        # Actions: 0 = Noop, 1 = Boost, 2 = Throttle, 3 = Isolate
        self.num_actions = 4
        self.state_bins = [10, 10, 10, 4] # Discrete bins for Q-table
        self.q_table = np.zeros(self.state_bins + [self.num_actions])
        
        self.load_config()
        self.load_model()
        
    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '../configs/config.yaml')
        try:
            with open(config_path, 'r') as f:
                c = yaml.safe_load(f)
                self.alpha = c['rl_engine']['alpha']
                self.gamma = c['rl_engine']['gamma']
                self.epsilon = c['rl_engine']['epsilon']
                self.save_path = c['rl_engine']['save_path']
        except Exception:
            self.alpha, self.gamma, self.epsilon = 0.05, 0.9, 0.1
            self.save_path = "/tmp/rl_qtable.npy"
            
    def load_model(self):
        if os.path.exists(self.save_path):
            try:
                self.q_table = np.load(self.save_path)
            except:
                pass

    def save_model(self):
        np.save(self.save_path, self.q_table)

    def _discretize(self, state):
        cpu = min(int(state.get('cpu_usage', 0.0) * 10), 9)
        mem = min(int(state.get('mem_pressure', 0.0) * 10), 9)
        io = min(int(state.get('io_wait', 0.0) * 10), 9)
        
        class_str = state.get('process_class', 'Background')
        if class_str == "System Critical": c = 0
        elif class_str == "Interactive": c = 1
        elif class_str == "Background": c = 2
        else: c = 3
        
        return (cpu, mem, io, c)
        
    def choose_action(self, state):
        d_state = self._discretize(state)
        
        if np.random.uniform(0, 1) < self.epsilon:
            return np.random.randint(0, self.num_actions)
        else:
            return np.argmax(self.q_table[d_state])
            
    def learn(self, old_state, action, reward, new_state):
        s = self._discretize(old_state)
        s_next = self._discretize(new_state)
        
        predict = self.q_table[s][action]
        target = reward + self.gamma * np.max(self.q_table[s_next])
        self.q_table[s][action] = self.q_table[s][action] + self.alpha * (target - predict)

    def action_to_target_score(self, action):
        # Target score dictates what the PID controller will aim for.
        # Action 0 = Noop -> 0.5
        # Action 1 = Boost -> 1.0 (allow max resource)
        # Action 2 = Throttle -> 0.2 (strict limit)
        # Action 3 = Isolate -> 0.0 (severely strict)
        if action == 0: return 0.5
        if action == 1: return 1.0
        if action == 2: return 0.2
        if action == 3: return 0.0
        return 0.5

    def action_name(self, action):
        return ["Noop", "Boost", "Throttle", "Isolate"][action]
