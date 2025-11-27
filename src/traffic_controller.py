import os
import sys
import traci

def get_config_path():
    """
    Proje yapısına göre environment klasöründeki osm.sumocfg dosyasının 
    tam yolunu bulur.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    # Klasör yolunu senin son yapına göre güncelledim
    config_path = os.path.join(root_dir, "environment", "FourwayIntersection", "osm.sumocfg")
    return config_path

def run_simulation():
    print("--- Simülasyon Başlatılıyor ---")

    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("HATA: Lütfen bilgisayarınızda 'SUMO_HOME' ortam değişkenini tanımlayın.")

    config_file = get_config_path()
    if not os.path.exists(config_file):
        print(f"HATA: Config dosyası bulunamadı!\nAranan yol: {config_file}")
        return

    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c", config_file]

    try:
        traci.start(sumoCmd)
    except Exception as e:
        print(f"SUMO başlatılırken hata oluştu: {e}")
        return

    traffic_lights = traci.trafficlight.getIDList()
    
    if not traffic_lights:
        print("UYARI: Bu haritada kontrol edilecek trafik ışığı bulunamadı!")
        tl_id = None
    else:
        tl_id = traffic_lights[0]
        print(f"\n-> Tespit edilen trafik ışıkları: {traffic_lights}")
        print(f"-> Kontrol edilecek aktif ışık ID'si: {tl_id}\n")

    # --- DÖNGÜ BAŞLIYOR ---
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        if tl_id and step % 30 == 0:
            try:
                # 1. Mevcut fazı al (Örn: 3)
                current_phase = traci.trafficlight.getPhase(tl_id)
                
                # 2. Işığın TOPLAM kaç fazı olduğunu dinamik olarak öğren
                # (Böylece 4 fazlı ışıkta da, 8 fazlı ışıkta da çalışır)
                program_logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
                total_phases = len(program_logic.phases)

                # 3. Modulo (%) kullanarak bir sonraki fazı hesapla
                # Örnek: (3 + 1) % 4 işleminin sonucu 0 olur. Böylece başa döner.
                next_phase = (current_phase + 1) % total_phases
                
                traci.trafficlight.setPhase(tl_id, next_phase)
                
                print(f"Saniye {step}: Faz değiştirildi. ({current_phase} -> {next_phase})")
            except Exception as e:
                print(f"Işık değiştirilirken hata: {e}")

        step += 1

    traci.close()
    print("Simülasyon tamamlandı.")

if __name__ == "__main__":
    run_simulation()