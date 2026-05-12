import os
from stable_baselines3 import DQN
from sumo_env import SumoEnvironment

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_PATH = os.path.join(ROOT_DIR, "environment", "FourwayIntersection", "osm.sumocfg")
MODEL_SAVE_PATH = os.path.join(ROOT_DIR, "models", "dqn_sumo_model_checkpoint_10000_steps")

TRAFFIC_LIGHT_ID = "cluster_1345077844_2589681474_8228683608_8228683609"

CAMERA_EDGES = {
    0: ["264388791#1"],             
    1: ["252967348#1", "252967348#0"], 
    2: ["884871893#1"],              
    3: ["169460470#1"]               
}

def test_model():
    print("--- EĞİTİLMİŞ RL MODELİ TEST EDİLİYOR ---")

    env = SumoEnvironment(config_path=CONFIG_PATH, tl_id=TRAFFIC_LIGHT_ID, camera_edges=CAMERA_EDGES, gui=True)

    if not os.path.exists(MODEL_SAVE_PATH + ".zip"):
        print("HATA: Eğitilmiş model bulunamadı!")
        return
        
    model = DQN.load(MODEL_SAVE_PATH)
    
    obs, info = env.reset()
    done = False
    step_count = 0
    
    while not done:
        action, _states = model.predict(obs, deterministic=True)
        action = int(action.item()) 
        
        obs, reward, done, truncated, info = env.step(action)
        
        k_skor = round(float(obs[0]), 1)
        g_skor = round(float(obs[1]), 1)
        d_skor = round(float(obs[2]), 1)
        b_skor = round(float(obs[3]), 1)
        
        # ÇÖZÜM BURADA: info sözlüğünde 'total_score' varsa onu al, yoksa 'total_queue' al.
        toplam_ham = info.get('total_score', info.get('total_queue', 0))
        toplam = round(float(toplam_ham), 1)
        
        print(f"Adım {step_count} | AI Seçimi: {action} | "
              f"Talep -> K: {k_skor}, G: {g_skor}, D: {d_skor}, B: {b_skor} | "
              f"Ödül: {round(reward, 1)}")
              
        step_count += 1

    env.close()

if __name__ == "__main__":
    test_model()