import os
import sys
import traci

# --- AYARLAR ---
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           "..", "environment", "FourwayIntersection", "osm.sumocfg")
SUMO_BINARY = "sumo-gui" # İzlemek için gui, hızlı bitirmek için "sumo"

def run_baseline():
    # 1. SUMO Ortam Kurulumu
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("Hütfen SUMO_HOME değişkenini tanımlayın.")

    # 2. Simülasyonu Başlat (Işıklara müdahale etmeyeceğiz!)
    sumoCmd = [SUMO_BINARY, "-c", CONFIG_PATH]
    traci.start(sumoCmd)

    print("--- Baseline (Sabit Döngü) Simülasyonu Başladı ---")
    print("Sistem Netedit'te ayarlanan 30sn Yeşil / 3sn Sarı döngüsünü uygulayacak.")

    step = 0
    # 3600 saniye (1 saat) boyunca çalıştır
    while step < 3600:
        traci.simulationStep() # Sadece ilerletiyoruz, setPhase YOK.
        step += 1
    
    traci.close()
    print("Baseline testi tamamlandı.")

if __name__ == "__main__":
    run_baseline()