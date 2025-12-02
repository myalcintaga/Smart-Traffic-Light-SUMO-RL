import os
import csv
import sys

# SUMO / TraCI import güvenliği
try:
    import traci
except Exception:
    if "SUMO_HOME" in os.environ:
        sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
        import traci
    else:
        raise RuntimeError("SUMO_HOME environment variable not set and traci import failed.")

# Konfigürasyon
CONTROL_INTERVAL = 5
BASE_GREEN = 5
K = 1
MAX_GREEN = 60
DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "environment", "FourwayIntersection", "osm.sumocfg")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "sumo_control_log.csv")

def _get_sumo_binary(use_gui=True):
    return "sumo-gui" if use_gui else "sumo"

def _start_sumo(config_file, use_gui=True):
    if "SUMO_HOME" not in os.environ:
        raise RuntimeError("SUMO_HOME not set. Set SUMO_HOME to SUMO installation directory.")
    sumo_binary = _get_sumo_binary(use_gui)
    traci.start([sumo_binary, "-c", config_file])

def _get_phase_lanes(tl_id, phase_index):
    logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
    if phase_index >= len(logic.phases):
        return []
    state = logic.phases[phase_index].state
    controlled = traci.trafficlight.getControlledLinks(tl_id)
    lanes = []
    for i, ch in enumerate(state):
        if i < len(controlled) and ch.upper() == "G":
            for mov in controlled[i]:
                if mov and len(mov) >= 1:
                    lanes.append(mov[0])
    return list(set(lanes))

def _phase_demand_by_lanes(lanes):
    total = 0
    for lane in lanes:
        try:
            total += traci.lane.getLastStepVehicleNumber(lane)
        except Exception:
            pass
    return total

def _select_best_phase(tl_id):
    logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
    best_idx = 0
    best_d = -1
    for idx in range(len(logic.phases)):
        lanes = _get_phase_lanes(tl_id, idx)
        d = _phase_demand_by_lanes(lanes)
        if d > best_d:
            best_d = d
            best_idx = idx
    return best_idx, best_d

def _ensure_log_dir(path):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "tl_id", "selected_phase", "demand", "duration"])

def run_simulation(config_path=None, use_gui=False, sim_duration=None):
    config_path = config_path or DEFAULT_CONFIG
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")
    _ensure_log_dir(LOG_PATH)
    _start_sumo(config_path, use_gui=use_gui)

    tl_ids = traci.trafficlight.getIDList()
    if not tl_ids:
        print("Uyarı: trafik ışığı bulunamadı.")

    step = 0
    try:
        if sim_duration is not None:
            # Süreli çalışma: belirtilen saniye kadar devam et
            end_time = float(sim_duration)
            while traci.simulation.getTime() < end_time:
                if step % CONTROL_INTERVAL == 0:
                    for tl in tl_ids:
                        try:
                            best_phase, demand = _select_best_phase(tl)
                            duration = int(BASE_GREEN + K * demand)
                            duration = max(BASE_GREEN, min(duration, MAX_GREEN))
                            traci.trafficlight.setPhase(tl, best_phase)
                            with open(LOG_PATH, "a", newline="") as f:
                                csv.writer(f).writerow([step, tl, best_phase, demand, duration])
                            for _ in range(duration):
                                traci.simulationStep()
                                step += 1
                        except Exception as e:
                            print(f"TL kontrol hatası ({tl}): {e}")
                    continue
                traci.simulationStep()
                step += 1
        else:
            # Varsayılan: araç kalmayana kadar
            while traci.simulation.getMinExpectedNumber() > 0:
                if step % CONTROL_INTERVAL == 0:
                    for tl in tl_ids:
                        try:
                            best_phase, demand = _select_best_phase(tl)
                            duration = int(BASE_GREEN + K * demand)
                            duration = max(BASE_GREEN, min(duration, MAX_GREEN))
                            traci.trafficlight.setPhase(tl, best_phase)
                            with open(LOG_PATH, "a", newline="") as f:
                                csv.writer(f).writerow([step, tl, best_phase, demand, duration])
                            for _ in range(duration):
                                traci.simulationStep()
                                step += 1
                        except Exception as e:
                            print(f"TL kontrol hatası ({tl}): {e}")
                    continue
                traci.simulationStep()
                step += 1
    finally:
        traci.close()
        print("Simülasyon kapandı. Log:", LOG_PATH)

if __name__ == "__main__":
    # Kullanım: python sumo_traffic_controller.py [config_path] [--gui]
    cfg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    gui = any(arg == "--gui" for arg in sys.argv[1:])
    # Destek: --duration=3600
    duration_arg = next((arg for arg in sys.argv[1:] if arg.startswith("--duration=")), None)
    duration = float(duration_arg.split("=",1)[1]) if duration_arg else None
    run_simulation(cfg, use_gui=gui, sim_duration=duration)