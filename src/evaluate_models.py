import os
import sys
import traci
import matplotlib.pyplot as plt
from stable_baselines3 import DQN
from sumo_env import SumoEnvironment

# --- PROJECT PATHS ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_PATH = os.path.join(ROOT_DIR, "environment", "FourwayIntersection", "osm.sumocfg")
MODEL_SAVE_PATH = os.path.join(ROOT_DIR, "models", "dqn_sumo_model_checkpoint_10000_steps")

TRAFFIC_LIGHT_ID = "cluster_1345077844_2589681474_8228683608_8228683609"
SIM_DURATION = 3600

CAMERA_EDGES = {
    0: ["264388791#1"],             
    1: ["252967348#1", "252967348#0"], 
    2: ["884871893#1"],              
    3: ["169460470#1"]               
}

def get_total_queue():
    """Counts the total halting vehicles across all camera edges."""
    total = 0
    for edges in CAMERA_EDGES.values():
        for edge_id in edges:
            try:
                total += traci.edge.getLastStepHaltingNumber(edge_id)
            except: pass
    return total

# ==========================================
# 1. ACTUATED (RULE-BASED) SYSTEM TEST
# ==========================================
def run_actuated():
    print("\n--- ROUND 1: ACTUATED (RULE-BASED) SYSTEM RUNNING ---")
    traci.start(["sumo", "-c", CONFIG_PATH, "--no-step-log", "true", "--time-to-teleport", "150"])
    
    times = []
    queues = []
    
    tl_state = {"current_phase": 0, "phase_start_time": 0.0, "min_phase_time": 15}
    step = 0
    
    # Dictionary for Green to Yellow phase transitions
    phase_to_yellow = {6: 7, 2: 3, 0: 1, 4: 5}
    
    while step < SIM_DURATION:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        
        times.append(sim_time)
        queues.append(get_total_queue())

        if step % 3 == 0:
            current_phase = tl_state["current_phase"]
            time_in_phase = sim_time - tl_state["phase_start_time"]
            
            if time_in_phase >= tl_state["min_phase_time"]:
                logic = traci.trafficlight.getAllProgramLogics(TRAFFIC_LIGHT_ID)[0]
                best_idx = 0
                best_d = -1
                
                for idx in range(len(logic.phases)):
                    if logic.phases[idx].duration < 5: continue
                    
                    action_map = {6: 0, 2: 1, 0: 2, 4: 3}
                    if idx in action_map:
                        action = action_map[idx]
                        d = sum([traci.edge.getLastStepHaltingNumber(e) for e in CAMERA_EDGES[action]])
                        if d > best_d:
                            best_d = d
                            best_idx = idx
                
                # FAIR COMPETITION: 3 seconds yellow light before switching green phase
                if best_idx != current_phase:
                    # Switch to yellow
                    yellow_phase = phase_to_yellow.get(current_phase, current_phase)
                    traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, yellow_phase)
                    
                    # Advance simulation by 3 seconds for yellow light
                    for _ in range(3):
                        traci.simulationStep()
                        sim_time = traci.simulation.getTime()
                        step += 1
                        times.append(sim_time)
                        queues.append(get_total_queue())
                        
                    # 3 seconds passed, switch to the new green phase
                    traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, best_idx)
                    tl_state["current_phase"] = best_idx
                    tl_state["phase_start_time"] = sim_time
                    
        step += 1
        
    traci.close()
    return times, queues

# ==========================================
# 2. DEEP RL (DQN) SYSTEM TEST
# ==========================================
def run_rl():
    print("\n--- ROUND 2: DEEP RL (DQN) SYSTEM RUNNING ---")
    env = SumoEnvironment(config_path=CONFIG_PATH, tl_id=TRAFFIC_LIGHT_ID, camera_edges=CAMERA_EDGES, gui=False)
    
    if not os.path.exists(MODEL_SAVE_PATH + ".zip"):
        print(f"ERROR: Model not found ({MODEL_SAVE_PATH}.zip)")
        env.close()
        return [], []
        
    model = DQN.load(MODEL_SAVE_PATH)
    
    times = []
    queues = []
    
    obs, info = env.reset()
    done = False
    
    while not done:
        action, _states = model.predict(obs, deterministic=True)
        action = int(action.item()) 
        
        obs, reward, done, truncated, info = env.step(action)
        
        sim_time = traci.simulation.getTime()
        times.append(sim_time)
        queues.append(get_total_queue())
        
    env.close()
    return times, queues

# ==========================================
# 3. FIXED-CYCLE SYSTEM TEST (90s Green)
# ==========================================
def run_fixed():
    print("\n--- ROUND 3: FIXED-CYCLE SYSTEM RUNNING ---")
    traci.start(["sumo", "-c", CONFIG_PATH, "--no-step-log", "true", "--time-to-teleport", "150"])
    
    times = []
    queues = []
    
    # Phase sequence representing: Green(0) -> Yellow(1) -> Green(2) -> Yellow(3) -> Green(4) -> Yellow(5) -> Green(6) -> Yellow(7)
    phase_sequence = [0, 1, 2, 3, 4, 5, 6, 7]
    # Durations: 90s for Green, 3s for Yellow
    phase_durations = {0: 90, 1: 3, 2: 90, 3: 3, 4: 90, 5: 3, 6: 90, 7: 3}
    
    current_phase_idx = 0
    traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, phase_sequence[current_phase_idx])
    phase_start_time = 0.0
    
    step = 0
    while step < SIM_DURATION:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        
        times.append(sim_time)
        queues.append(get_total_queue())
        
        time_in_phase = sim_time - phase_start_time
        current_phase = phase_sequence[current_phase_idx]
        
        # Check if it's time to switch phase
        if time_in_phase >= phase_durations[current_phase]:
            current_phase_idx = (current_phase_idx + 1) % len(phase_sequence) # Loop back to 0 if at the end
            traci.trafficlight.setPhase(TRAFFIC_LIGHT_ID, phase_sequence[current_phase_idx])
            phase_start_time = sim_time
            
        step += 1
        
    traci.close()
    return times, queues

# ==========================================
# 4. PLOTTING RESULTS
# ==========================================
def plot_results(act_t, act_q, rl_t, rl_q, fix_t, fix_q):
    if not act_t or not rl_t or not fix_t:
        print("ERROR: Missing data. Cannot plot chart.")
        return
        
    print("\n--- CALCULATING RESULTS & DRAWING CHART ---")
    
    plt.figure(figsize=(14, 7))
    
    # Plotting all 3 systems
    plt.plot(fix_t, fix_q, label='Fixed-Cycle (90s Green)', color='gray', alpha=0.6, linewidth=1.5)
    plt.plot(act_t, act_q, label='Actuated (Rule-Based)', color='red', alpha=0.7, linewidth=1.5)
    plt.plot(rl_t, rl_q, label='Proposed DQN Agent', color='blue', alpha=0.9, linewidth=2)
    
    # English Labels for the Poster
    plt.title("Performance Comparison: Traffic Light Control Systems", fontsize=16, fontweight='bold')
    plt.xlabel("Simulation Time (Seconds)", fontsize=12)
    plt.ylabel("Total Waiting Vehicles at Intersection", fontsize=12)
    plt.legend(fontsize=11, loc="upper left")
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Save the chart
    save_path = os.path.join(ROOT_DIR, "data", "logs", "performance_comparison_en.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight') 
    print(f"Comparison chart saved to: {save_path}")
    
    plt.show()

if __name__ == "__main__":
    if 'SUMO_HOME' not in os.environ:
        sys.exit("ERROR: SUMO_HOME not found in environment variables.")
        
    # Execute rounds sequentially
    act_times, act_queues = run_actuated()
    rl_times, rl_queues = run_rl()
    fix_times, fix_queues = run_fixed()
    
    # Draw the final 3-line chart
    plot_results(act_times, act_queues, rl_times, rl_queues, fix_times, fix_queues)