import os
import sys
import traci
import random
import csv
from vision_helper import TrafficVision

# --- CONSTANTS & CONFIGURATION ---
# Paths and Files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

MODEL_PATH = os.path.join(ROOT_DIR, "models", "best.pt")
VIDEO_PATH = os.path.join(ROOT_DIR, "data", "test_data", "test_video.mp4")
CONFIG_PATH = os.path.join(ROOT_DIR, "environment", "FourwayIntersection", "osm.sumocfg")
LOG_PATH = os.path.join(ROOT_DIR, "data", "logs", "smart_twin_log.csv")

# Digital Twin Settings
SUMO_EDGE_ID = "264388791#1"  # Edge ID observed by the camera
SUMO_ROUTE_ID = "N_to_S"      # Route ID for vehicles spawned on that edge

# Traffic Light Algorithm Settings (Actuated Control)
CONTROL_INTERVAL = 3      # Check traffic lights every 3 seconds
MAX_GREEN = 90            # Maximum green phase duration
MIN_GREEN = 10            # Minimum green phase duration
DEMAND_THRESHOLD = 0.15   # Threshold for demand difference to switch phase

def _get_phase_lanes(tl_id, phase_index):
    """
    Identifies which lanes have a GREEN light in the given phase index.
    """
    logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
    if phase_index >= len(logic.phases): return []
    state = logic.phases[phase_index].state
    controlled = traci.trafficlight.getControlledLinks(tl_id)
    lanes = []
    for i, ch in enumerate(state):
        # 'G' or 'g' means Green
        if i < len(controlled) and (ch.upper() == "G" or ch.upper() == "g"):
            for mov in controlled[i]:
                if mov: lanes.append(mov[0])
    return list(set(lanes))

def _phase_demand_by_lanes(lanes):
    """
    Calculates the total number of vehicles (queue length) on the specified lanes.
    """
    total = 0
    for lane in lanes:
        try: total += traci.lane.getLastStepVehicleNumber(lane)
        except: pass
    return total

def _select_best_phase(tl_id):
    """
    Selects the BEST phase based on current vehicle density (Greedy Approach).
    Returns: (best_phase_index, best_demand_value)
    """
    logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
    best_idx = 0; best_d = -1
    
    for idx in range(len(logic.phases)):
        # Skip yellow phases (Assume phases shorter than 5s are yellow/transition)
        if logic.phases[idx].duration < 5: continue

        lanes = _get_phase_lanes(tl_id, idx)
        d = _phase_demand_by_lanes(lanes)
        if d > best_d:
            best_d = d; best_idx = idx
    return best_idx, best_d

def run_smart_simulation():
    print("--- STARTING SMART DIGITAL TWIN ---")
    
    # 1. Start Vision System
    try:
        vision = TrafficVision(MODEL_PATH, VIDEO_PATH)
        video_active = True
    except Exception as e:
        print(f"Vision System Failed (Running Simulation Only): {e}")
        video_active = False

    # 2. Start SUMO
    if 'SUMO_HOME' in os.environ:
        sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
    
    # Prepare Log File
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", newline="") as f:
        csv.writer(f).writerow(["time", "tl_id", "current_phase", "queue_len", "action", "camera_detected"])

    print("Initializing SUMO...")
    traci.start(["sumo-gui", "-c", CONFIG_PATH])
    
    # Traffic Light State Memory
    tl_ids = traci.trafficlight.getIDList()
    tl_state = {tl: {"current_phase": 0, "phase_start_time": 0} for tl in tl_ids}

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        
        # --- SECTION 1: DIGITAL TWIN (CAMERA SYNCHRONIZATION) ---
        detected_count = 0
        if video_active:
            cam_count, frame = vision.get_vehicle_count()
            if cam_count == -1:
                print(f"Video finished. Camera disabled.")
                video_active = False
            else:
                detected_count = cam_count
                try:
                    sumo_count = traci.edge.getLastStepVehicleNumber(SUMO_EDGE_ID)
                except: sumo_count = 0
                
                diff = cam_count - sumo_count
                if diff > 0:
                    print(f"Sync: Camera={cam_count} > SUMO={sumo_count}. Injecting {diff} vehicles.")
                    for i in range(diff):
                        try:
                            lane_idx = random.choice([0, 1])
                            # Inject vehicle into simulation
                            traci.vehicle.add(f"twin_{step}_{i}", SUMO_ROUTE_ID, "standard_car", departLane=str(lane_idx), departPos="base")
                        except: pass

        # --- SECTION 2: ACTUATED TRAFFIC LIGHT (ALGORITHM) ---
        if step % CONTROL_INTERVAL == 0:
            for tl in tl_ids:
                try:
                    state = tl_state[tl]
                    current_phase = state["current_phase"]
                    time_in_phase = sim_time - state["phase_start_time"]
                    
                    # Analyze Traffic
                    current_lanes = _get_phase_lanes(tl, current_phase)
                    current_demand = _phase_demand_by_lanes(current_lanes)
                    best_phase, best_demand = _select_best_phase(tl)

                    should_change = False
                    action = "HOLD"

                    # Has the minimum green time passed?
                    if time_in_phase >= MIN_GREEN:
                        # 1. Is there a significant demand difference?
                        if best_phase != current_phase:
                            if best_demand > current_demand * (1 + DEMAND_THRESHOLD):
                                should_change = True
                                action = "CHANGE_DEMAND"
                        
                        # 2. Has the maximum green time passed?
                        if time_in_phase >= MAX_GREEN:
                            should_change = True
                            best_phase, _ = _select_best_phase(tl) # Force switch to best phase
                            action = "TIMEOUT"

                    if should_change:
                        traci.trafficlight.setPhase(tl, best_phase)
                        tl_state[tl]["current_phase"] = best_phase
                        tl_state[tl]["phase_start_time"] = sim_time
                        print(f"TL {tl}: {action} -> Phase {best_phase} (Demand: {best_demand})")

                    # Logging (Including Camera Data)
                    with open(LOG_PATH, "a", newline="") as f:
                        csv.writer(f).writerow([int(sim_time), tl, current_phase, current_demand, action, detected_count])

                except Exception as e: print(f"TL Error: {e}")

        step += 1

    if video_active: vision.release()
    traci.close()
    print(f"Simulation Finished. Logs saved to: {LOG_PATH}")

if __name__ == "__main__":
    run_smart_simulation()