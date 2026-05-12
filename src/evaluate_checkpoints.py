import os
import sys
import glob
import re
import traci
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import DQN
from sumo_env import SumoEnvironment

# --- PROJECT PATHS ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_PATH = os.path.join(ROOT_DIR, "environment", "FourwayIntersection", "osm.sumocfg")
MODELS_DIR = os.path.join(ROOT_DIR, "models")

TRAFFIC_LIGHT_ID = "cluster_1345077844_2589681474_8228683608_8228683609"

CAMERA_EDGES = {
    0: ["264388791#1"],             
    1: ["252967348#1", "252967348#0"], 
    2: ["884871893#1"],              
    3: ["169460470#1"]               
}

def get_total_queue():
    """Counts the halting vehicles within our camera view."""
    total = 0
    for edges in CAMERA_EDGES.values():
        for edge_id in edges:
            try:
                total += traci.edge.getLastStepHaltingNumber(edge_id)
            except: pass
    return total

def evaluate_model(model_path):
    """Tests the given model in a 1-hour simulation and returns the average queue."""
    env = SumoEnvironment(config_path=CONFIG_PATH, tl_id=TRAFFIC_LIGHT_ID, camera_edges=CAMERA_EDGES, gui=False)
    model = DQN.load(model_path)
    
    obs, info = env.reset()
    done = False
    
    total_queues = []
    
    while not done:
        action, _states = model.predict(obs, deterministic=True)
        action = int(action.item()) 
        
        obs, reward, done, truncated, info = env.step(action)
        total_queues.append(get_total_queue())
        
    env.close()
    
    # Calculate the mean of all queues formed during the simulation
    return np.mean(total_queues)

def main():
    if 'SUMO_HOME' not in os.environ:
        sys.exit("ERROR: SUMO_HOME not found.")

    print("--- SEARCHING FOR CHECKPOINT MODELS ---")
    
    # Find all checkpoint zip files
    search_pattern = os.path.join(MODELS_DIR, "dqn_sumo_model_checkpoint_*_steps.zip")
    checkpoint_files = glob.glob(search_pattern)
    
    if not checkpoint_files:
        print("ERROR: No checkpoint files found!")
        return

    # Extract step numbers from filenames to sort them numerically
    def extract_step(filepath):
        match = re.search(r'checkpoint_(\d+)_steps', filepath)
        return int(match.group(1)) if match else 0

    checkpoint_files.sort(key=extract_step)

    steps_labels = []
    avg_queues = []

    print("\n--- TESTING STARTED (This may take a few minutes depending on the number of models) ---")
    for file in checkpoint_files:
        step_num = extract_step(file)
        print(f"Testing {step_num}-step model...", end="", flush=True)
        
        avg_queue = evaluate_model(file)
        
        print(f" -> Average Queue: {avg_queue:.2f} vehicles")
        
        # Format labels nicely for the chart (e.g., "10k", "20k")
        steps_labels.append(f"{step_num // 1000}k")
        avg_queues.append(avg_queue)

    print("\n--- ALL TESTS COMPLETED, DRAWING CHART ---")

    # Create the bar chart
    plt.figure(figsize=(12, 6))
    bars = plt.bar(steps_labels, avg_queues, color='skyblue', edgecolor='black', alpha=0.8)

    # Find the model with the best performance (lowest queue) and color it green
    best_idx = np.argmin(avg_queues)
    bars[best_idx].set_color('lightgreen')
    bars[best_idx].set_edgecolor('green')
    
    # Write the values on top of the bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, round(yval, 1), ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Chart formatting in English
    plt.title("AI Performance by Training Steps (Lower is better)", fontsize=14)
    plt.xlabel("Training Steps (Thousands)", fontsize=12)
    plt.ylabel("Average Intersection Queue (Number of Vehicles)", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Save the chart
    save_path = os.path.join(ROOT_DIR, "data", "logs", "checkpoint_evaluation_en.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path)
    print(f"\nChart saved to: {save_path}")

    plt.show()

if __name__ == "__main__":
    main()