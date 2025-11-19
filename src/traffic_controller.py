import os
import sys
import traci

def get_config_path():
    """
    Proje yapısına göre environment klasöründeki osm.sumocfg dosyasının 
    tam yolunu bulur.
    """
    # Şu anki dosyanın (src/traffic_controller.py) bulunduğu klasör
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Proje ana dizini (Smart-Traffic-Light-SUMO-RL)
    root_dir = os.path.dirname(current_dir)
    
    # Config dosyasının yolu (OSM'den indirdiğin dosya ismi)
    config_path = os.path.join(root_dir, "environment", "osm.sumocfg")
    return config_path

def run_simulation():
    print("--- Simülasyon Başlatılıyor ---")

    # 1. SUMO_HOME Ortam Değişkeni Kontrolü
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("HATA: Lütfen bilgisayarınızda 'SUMO_HOME' ortam değişkenini tanımlayın.")

    # 2. Konfigürasyon Dosyasını Kontrol Et
    config_file = get_config_path()
    if not os.path.exists(config_file):
        print(f"HATA: Config dosyası bulunamadı!\nAranan yol: {config_file}")
        print("Lütfen 'environment' klasöründe 'osm.sumocfg' olduğundan emin olun.")
        return

    # 3. SUMO'yu Başlatma (sumo-gui: Arayüzlü, sumo: Arayüzsüz)
    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c", config_file]

    # TraCI Bağlantısını Başlat
    try:
        traci.start(sumoCmd)
    except Exception as e:
        print(f"SUMO başlatılırken hata oluştu: {e}")
        return

    # 4. Haritadaki Trafik Işıklarını Otomatik Bul
    traffic_lights = traci.trafficlight.getIDList()
    
    if not traffic_lights:
        print("UYARI: Bu haritada kontrol edilecek trafik ışığı bulunamadı!")
        # Işık yoksa bile simülasyonu izlemek için devam edebiliriz
        tl_id = None
    else:
        # Listeden ilk ışığı seçip onu kontrol edelim
        tl_id = traffic_lights[0]
        print(f"\n-> Tespit edilen trafik ışıkları: {traffic_lights}")
        print(f"-> Kontrol edilecek aktif ışık ID'si: {tl_id}\n")

    # 5. Simülasyon Döngüsü
    step = 0
    # Araç olduğu sürece veya belirli bir süre (örn: 3600 adım) çalış
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep() # Simülasyonu 1 saniye ilerlet

        # --- BASİT KONTROL MANTIĞI (TEST İÇİN) ---
        # Eğer bir trafik ışığı bulduysak, her 30 saniyede bir fazını değiştir
        if tl_id and step % 30 == 0:
            try:
                current_phase = traci.trafficlight.getPhase(tl_id)
                next_phase = current_phase + 1
                
                # Işığın fazını değiştir (SUMO'nun kendi döngüsü içinde)
                traci.trafficlight.setPhase(tl_id, next_phase)
                
                print(f"Saniye {step}: Faz değiştirildi. ({current_phase} -> {next_phase})")
            except Exception as e:
                print(f"Işık değiştirilirken hata: {e}")

        step += 1

    # 6. Kapatma
    traci.close()
    print("Simülasyon tamamlandı.")

if __name__ == "__main__":
    run_simulation()