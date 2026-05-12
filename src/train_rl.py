import os
import sys
from stable_baselines3 import DQN
from stable_baselines3.common.env_checker import check_env
from sumo_env import SumoEnvironment

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_PATH = os.path.join(ROOT_DIR, "environment", "FourwayIntersection", "osm.sumocfg")
MODEL_SAVE_PATH = os.path.join(ROOT_DIR, "models", "dqn_sumo_model_v2")

TRAFFIC_LIGHT_ID = "cluster_1345077844_2589681474_8228683608_8228683609"

# --- EKLENEN KISIM: ESNEK KAMERA YOLLARI ---
# LÜTFEN NETEDIT'TEN BAKARAK BURADAKİ ID'LERİ KENDİ HARİTANA GÖRE DOLDUR!
CAMERA_EDGES = {
    0: ["264388791#1"],             # Kuzey: 1 yol
    1: ["252967348#1", "252967348#0"], # Güney: 2 yol
    2: ["884871893#1"],              # Doğu: 1 yol
    3: ["169460470#1"]               # Batı: 1 yol
}

import os
import sys
from stable_baselines3 import DQN
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.callbacks import CheckpointCallback # EKLENDİ
from sumo_env import SumoEnvironment

# ... (Yol tanımlamaları ve CAMERA_EDGES aynı kalacak) ...

def train():
    print("--- RL EĞİTİMİ (TRAINING) BAŞLATILIYOR ---")
    
    env = SumoEnvironment(config_path=CONFIG_PATH, tl_id=TRAFFIC_LIGHT_ID, camera_edges=CAMERA_EDGES, gui=False)
    check_env(env, warn=True)

    model = DQN("MlpPolicy", env, learning_rate=1e-3, buffer_size=50000, exploration_fraction=0.1, exploration_initial_eps=1.0, exploration_final_eps=0.05, verbose=1)

    TRAINING_STEPS = 100000 
    print(f"\nAjan {TRAINING_STEPS} adım boyunca eğitiliyor...")
    
    # EKLENEN KISIM: Her 10.000 adımda bir modeli models klasörüne kaydet
    checkpoint_callback = CheckpointCallback(
        save_freq=10000, 
        save_path=os.path.dirname(MODEL_SAVE_PATH), 
        name_prefix="dqn_sumo_model_checkpoint"
    )
    
    # callback parametresini ekliyoruz
    model.learn(total_timesteps=TRAINING_STEPS, callback=checkpoint_callback)

    model.save(MODEL_SAVE_PATH)
    print(f"\nEğitim tamamlandı! Final modeli şuraya kaydedildi: {MODEL_SAVE_PATH}.zip")
    env.close()

if __name__ == "__main__":
    train()