import os
import csv
import sys
import traci

# --- SABİT AYARLAR ---
CONTROL_INTERVAL = 3      # 3 saniyede bir kontrol et
MAX_GREEN = 90            # Bir ışık en fazla 90 sn yeşil kalsın
MIN_GREEN = 10            # Bir ışık en az 10 sn yeşil kalsın
DEMAND_THRESHOLD = 0.15   # %15 talep farkı varsa ışığı değiştir
SIM_DURATION = 3600       # Simülasyon süresi (1 saat)

def get_config_path():
    """
    Proje yapısına göre environment klasöründeki osm.sumocfg dosyasının 
    tam yolunu bulur.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    # Environment klasörünüze göre yolu güncelledim
    config_path = os.path.join(root_dir, "environment", "FourwayIntersection", "osm.sumocfg")
    return config_path

def get_log_path():
    """
    Log dosyasının kaydedileceği yolu belirler.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    log_dir = os.path.join(root_dir, "data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "actuated_control_log.csv")

def _get_phase_lanes(tl_id, phase_index):
    """
    Verilen fazda (phase_index) hangi şeritlerin YEŞİL yandığını bulur.
    """
    logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
    if phase_index >= len(logic.phases):
        return []
    state = logic.phases[phase_index].state
    controlled = traci.trafficlight.getControlledLinks(tl_id)
    lanes = []
    for i, ch in enumerate(state):
        if i < len(controlled) and (ch.upper() == "G" or ch.upper() == "g"):
            for mov in controlled[i]:
                if mov and len(mov) >= 1:
                    lanes.append(mov[0])
    return list(set(lanes))

def _phase_demand_by_lanes(lanes):
    """
    Belirtilen şeritlerdeki toplam araç sayısını (kuyruk) hesaplar.
    """
    total = 0
    for lane in lanes:
        try:
            # Şeritte duran veya yavaş giden araçları sayar
            total += traci.lane.getLastStepVehicleNumber(lane)
            # Alternatif olarak kuyruk uzunluğu da alınabilir:
            # total += traci.lane.getLastStepHaltingNumber(lane)
        except Exception:
            pass
    return total

def _select_best_phase(tl_id):
    """
    Mevcut araç yoğunluğuna göre EN İYİ fazı seçer (Greedy Algorithm).
    """
    logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
    best_idx = 0
    best_d = -1
    
    # Sadece YEŞİL olan ana fazları kontrol et (Sarı fazları atla)
    # Bizim tablomuzda 0, 2, 4, 6 ana fazlardı (30 sn olanlar)
    for idx in range(len(logic.phases)):
        # Sarı fazları (süreleri kısa olanları) atlayabiliriz
        if logic.phases[idx].duration < 5: 
            continue

        lanes = _get_phase_lanes(tl_id, idx)
        d = _phase_demand_by_lanes(lanes)
        if d > best_d:
            best_d = d
            best_idx = idx
    return best_idx, best_d

def run_actuated_simulation():
    print("--- Actuated (Talep Bazlı) Kontrol Başlatılıyor ---")
    
    # 1. SUMO Ayarları
    if 'SUMO_HOME' in os.environ:
        sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
    else:
        sys.exit("HATA: SUMO_HOME bulunamadı.")

    config_path = get_config_path()
    if not os.path.exists(config_path):
        print(f"HATA: Config dosyası bulunamadı: {config_path}")
        return

    # Log dosyasını hazırla
    log_file = get_log_path()
    with open(log_file, "w", newline="") as f:
        csv.writer(f).writerow(["time", "tl_id", "current_phase", "queue_len", "action"])

    # Simülasyonu başlat
    traci.start(["sumo-gui", "-c", config_path])

    # 2. Hazırlık
    tl_ids = traci.trafficlight.getIDList()
    if not tl_ids:
        print("Trafik ışığı bulunamadı!")
        traci.close()
        return

    # Her ışığın durumunu hafızada tut
    tl_state = {}
    for tl in tl_ids:
        tl_state[tl] = {
            "current_phase": 0,
            "phase_start_time": 0.0,
            "min_phase_time": MIN_GREEN
        }

    # 3. Ana Döngü
    step = 0
    while step < SIM_DURATION:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()

        # Belirli aralıklarla (örn: 3 saniyede bir) karar ver
        if step % CONTROL_INTERVAL == 0:
            for tl in tl_ids:
                try:
                    state = tl_state[tl]
                    current_phase = state["current_phase"]
                    phase_start_time = state["phase_start_time"]
                    
                    # Mevcut fazda geçen süre
                    time_in_phase = sim_time - phase_start_time

                    # --- KARAR MEKANİZMASI ---
                    # 1. Minimum süre dolmadıysa değiştirme (Sürücüleri şaşırtma)
                    if time_in_phase < state["min_phase_time"]:
                        continue

                    # 2. Mevcut durum ve En iyi durum analizi
                    current_lanes = _get_phase_lanes(tl, current_phase)
                    current_demand = _phase_demand_by_lanes(current_lanes)
                    
                    best_phase, best_demand = _select_best_phase(tl)

                    should_change = False
                    action = "HOLD"

                    # 3. Eğer mevcut fazda çok beklemişsek ve başka yerde yoğunluk varsa
                    if best_phase != current_phase:
                        # Eğer başka bir fazda belirgin şekilde (%15) daha fazla araç varsa
                        if best_demand > current_demand * (1 + DEMAND_THRESHOLD):
                            should_change = True
                            action = "CHANGE_DEMAND"
                    
                    # 4. Maksimum süre dolduysa kesin değiştir
                    if time_in_phase >= MAX_GREEN:
                        should_change = True
                        best_phase, _ = _select_best_phase(tl) # En kalabalığa dön
                        action = "TIMEOUT"

                    # 5. Uygulama
                    if should_change:
                        traci.trafficlight.setPhase(tl, best_phase)
                        tl_state[tl]["current_phase"] = best_phase
                        tl_state[tl]["phase_start_time"] = sim_time
                        print(f"Saniye {int(sim_time)}: Işık {action} -> Faz {best_phase} (Talep: {best_demand})")

                    # Loglama
                    with open(log_file, "a", newline="") as f:
                        csv.writer(f).writerow([int(sim_time), tl, current_phase, current_demand, action])

                except Exception as e:
                    print(f"Hata ({tl}): {e}")

        step += 1

    traci.close()
    print(f"Simülasyon tamamlandı. Loglar kaydedildi: {log_file}")

if __name__ == "__main__":
    run_actuated_simulation()