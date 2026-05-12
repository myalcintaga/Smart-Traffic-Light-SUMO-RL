import os
from stable_baselines3 import DQN
from sumo_env import SumoEnvironment

# --- PROJE YOLLARI ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_PATH = os.path.join(ROOT_DIR, "environment", "FourwayIntersection", "osm.sumocfg")
MODEL_SAVE_PATH = os.path.join(ROOT_DIR, "models", "dqn_sumo_model")

# Trafik Işığı ID'si
TRAFFIC_LIGHT_ID = "cluster_1345077844_2589681474_8228683608_8228683609"

def test_model():
    print("--- EĞİTİLMİŞ RL MODELİ (YAPAY ZEKA) TEST EDİLİYOR ---")

    # 1. Ortamı GUI (Arayüz) açık şekilde başlat
    # Yapay zekanın ne yaptığını görmek için gui=True yapıyoruz
    env = SumoEnvironment(config_path=CONFIG_PATH, tl_id=TRAFFIC_LIGHT_ID, gui=True)

    # 2. Eğitilmiş modeli yükle
    if not os.path.exists(MODEL_SAVE_PATH + ".zip"):
        print("HATA: Eğitilmiş model bulunamadı! Önce train_rl.py çalıştırmalısın.")
        return
        
    model = DQN.load(MODEL_SAVE_PATH)
    print("Model başarıyla yüklendi. Simülasyon başlıyor...")

    # 3. Simülasyon Döngüsü (Yapay Zeka Direksiyonda)
    obs, info = env.reset()
    done = False
    step_count = 0
    
    while not done:
        action, _states = model.predict(obs, deterministic=True)
        
        # ÇÖZÜM BURADA: Numpy array'i (örn: [2]) alıp saf bir tam sayıya (örn: 2) çevirir.
        action = int(action.item()) 
        
        # Seçilen aksiyonu simülasyonda uygula
        obs, reward, done, truncated, info = env.step(action)
        
        # Kararları terminalden de takip edelim
        print(f"Adım {step_count} | AI Aksiyonu: {action} | Toplam Kuyruk: {info['total_queue']} | Ödül: {reward}")
        step_count += 1

    print("Test simülasyonu tamamlandı.")
    env.close()

if __name__ == "__main__":
    test_model()