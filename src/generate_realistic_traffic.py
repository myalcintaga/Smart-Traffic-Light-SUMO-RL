import os
import sys
import subprocess

# --- PROJE YOLLARI ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
ENV_DIR = os.path.join(ROOT_DIR, "environment", "FourwayIntersection")
NET_FILE = os.path.join(ENV_DIR, "osm.net.xml.gz")
OUTPUT_FILE = os.path.join(ENV_DIR, "realistic_traffic.rou.xml")

# --- SUMO ARAÇLARI YOLLARI Kontrolü ---
if 'SUMO_HOME' in os.environ:
    SUMO_TOOLS = os.path.join(os.environ['SUMO_HOME'], 'tools')
else:
    sys.exit("HATA: SUMO_HOME bulunamadı.")

RANDOM_TRIPS = os.path.join(SUMO_TOOLS, "randomTrips.py")

def generate_realistic_traffic():
    print("--- REALİSTİK ŞEHİR GENELİ TRAFİK OLUŞTURULUYOR ---")

    # randomTrips.py komutu
    # --end: Simülasyon süresi (3600 saniye = 1 saat)
    # --period: Araç doğma sıklığı (Ortalama 0.5 saniyede bir araç = 7200 araç).
    # --fringe-factor: 10 -> Araçların yolların en uç köşelerinden doğma olasılığını artırır.
    # Bu, araçların bizim kavşağımızda doğması yerine oraya "gelmesini" sağlar.
    command = [
        "python", RANDOM_TRIPS,
        "-n", NET_FILE,
        "-r", OUTPUT_FILE,
        "--end", "3600",
        "--period", "2",
        "--fringe-factor", "10",
        "--validate"
    ]

    print(f"Çalıştırılan komut: {' '.join(command)}")
    
    try:
        # Komutu terminalde çalıştır
        subprocess.check_call(command)
        print(f"\nTrafik dosyası başarıyla oluşturuldu: {OUTPUT_FILE}")
        print("Artık bu dosyayı 'osm.sumocfg' içinde kullanabilirsin.")
    except subprocess.CalledProcessError as e:
        print(f"\nHATA: Trafik oluşturulurken bir hata oluştu: {e}")

if __name__ == "__main__":
    generate_realistic_traffic()