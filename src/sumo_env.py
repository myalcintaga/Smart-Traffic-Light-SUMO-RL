import os
import sys
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import traci

class SumoEnvironment(gym.Env):
    """
    RL Ajanı için SUMO Trafik Işığı Ortamı.
    Starvation (Mahrumiyet) önleyici düşük katsayılı Sanal Araç mantığı kullanır.
    """
    def __init__(self, config_path, tl_id, camera_edges, gui=False):
        super(SumoEnvironment, self).__init__()
        
        self.config_path = config_path
        self.tl_id = tl_id
        self.camera_edges = camera_edges
        self.gui = gui
        
        if 'SUMO_HOME' in os.environ:
            sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
        else:
            sys.exit("HATA: SUMO_HOME bulunamadı.")

        self.action_space = spaces.Discrete(4)
        self.action_to_phase = {0: 6, 1: 2, 2: 0, 3: 4}
        self.phase_to_yellow = {6: 7, 2: 3, 0: 1, 4: 5}

        # Skorlar esnek olduğu için tavanı 5000 yaptık
        self.observation_space = spaces.Box(
            low=0, high=5000.0, shape=(5,), dtype=np.float32
        )

        self.current_action = 0
        self.sim_step = 0
        self.max_steps = 3600
        self.min_green_time = 15 # Erken kapanmayı engellemek için 15 saniye

        # Bekleme süresi katsayısı (Her 20 saniye = 1 Sanal Araç)
        self.wait_weight = 0.05 

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        try: traci.close()
        except: pass

        sumo_binary = "sumo-gui" if self.gui else "sumo"
        traci.start([sumo_binary, "-c", self.config_path, "--start", "--no-step-log", "true", "--waiting-time-memory", "10000", "--time-to-teleport", "150"])
        
        self.sim_step = 0
        self.current_action = 0
        traci.trafficlight.setPhase(self.tl_id, self.action_to_phase[self.current_action])
        
        return self._get_state(), {}

    def step(self, action):
        if action != self.current_action:
            yellow_phase = self.phase_to_yellow[self.action_to_phase[self.current_action]]
            traci.trafficlight.setPhase(self.tl_id, yellow_phase)
            for _ in range(3):
                traci.simulationStep()
                self.sim_step += 1
            
            self.current_action = action
            traci.trafficlight.setPhase(self.tl_id, self.action_to_phase[self.current_action])
        
        for _ in range(self.min_green_time):
            traci.simulationStep()
            self.sim_step += 1

        next_state = self._get_state()
        
        # ÖDÜL: Toplam Talep Skorunun negatifi
        total_score = np.sum(next_state[0:4])
        reward = -float(total_score)
        
        if total_score == 0:
            reward += 10.0

        done = self.sim_step >= self.max_steps
        
        return next_state, reward, done, False, {"total_score": total_score}

    def _get_state(self):
        """Duran araçlar + Düşük katsayılı bekleme süresi."""
        state_scores = []
        for action_idx in range(4): 
            score = 0.0
            for edge_id in self.camera_edges[action_idx]:
                try:
                    # 1. Duran araç sayısı (Temel Puan)
                    halt_count = traci.edge.getLastStepHaltingNumber(edge_id)
                    
                    # 2. Bekleme süresi (Sanal Araç Puanı)
                    wait_time = traci.edge.getWaitingTime(edge_id)
                    
                    # Talep Skoru Formülü
                    score += halt_count + (wait_time * self.wait_weight)
                except:
                    pass
            state_scores.append(score)
            
        return np.array([state_scores[0], state_scores[1], state_scores[2], state_scores[3], self.current_action], dtype=np.float32)

    def close(self):
        try: traci.close()
        except: pass