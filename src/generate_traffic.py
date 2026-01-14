import os
import random

# --- AYARLAR (BURAYI KENDİ HARİTANA GÖRE DOLDUR) ---
# Giriş yapan yolların ID'leri
NORTH_IN = "264388791#1" 
SOUTH_IN = "252967348#1"
EAST_IN  = "884871893#1"
WEST_IN  = "169460470#1"

# Çıkış yapan yolların ID'leri (Genelde girişin ters yönüdür)
NORTH_OUT = "252967348#3"
SOUTH_OUT = "264388791#3"
EAST_OUT  = "169458918#1"
WEST_OUT  = "884871893#3"

# Trafik Yoğunluğu (Saatlik araç sayısı)
TRAFFIC_VOLUME = 400  # Her yönden saatte 400 araç (Orta trafik)
SIM_DURATION = 3600    # Simülasyon süresi (saniye)

def generate_route_file():
    # Dosya yolu
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_file = os.path.join(base_dir, "environment", "FourwayIntersection", "mild_traffic.rou.xml")

    print(f"Rota dosyası oluşturuluyor: {output_file}")

    with open(output_file, "w") as routes:
        routes.write("""<routes>
    <vType id="standard_car" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="15" guiShape="passenger"/>
    <vType id="heavy_car" accel="1.0" decel="3.5" sigma="0.5" length="7" minGap="3.0" maxSpeed="10" guiShape="truck"/>
    
    <route id="N_to_S" edges="{} {}"/>
    <route id="N_to_E" edges="{} {}"/>
    <route id="N_to_W" edges="{} {}"/>

    <route id="S_to_N" edges="{} {}"/>
    <route id="S_to_E" edges="{} {}"/>
    <route id="S_to_W" edges="{} {}"/>

    <route id="E_to_W" edges="{} {}"/>
    <route id="E_to_N" edges="{} {}"/>
    <route id="E_to_S" edges="{} {}"/>

    <route id="W_to_E" edges="{} {}"/>
    <route id="W_to_N" edges="{} {}"/>
    <route id="W_to_S" edges="{} {}"/>
""".format(
            NORTH_IN, SOUTH_OUT, NORTH_IN, EAST_OUT, NORTH_IN, WEST_OUT,
            SOUTH_IN, NORTH_OUT, SOUTH_IN, EAST_OUT, SOUTH_IN, WEST_OUT,
            EAST_IN, WEST_OUT, EAST_IN, NORTH_OUT, EAST_IN, SOUTH_OUT,
            WEST_IN, EAST_OUT, WEST_IN, NORTH_OUT, WEST_IN, SOUTH_OUT
        ))

        # Akışları (Flows) Oluşturma
        # Her 4 saniyede bir rastgele araç ekle (Poisson dağılımı benzeri)
        # probability: Her saniye araç gelme ihtimali. 0.2 = %20 ihtimalle araç gelir.
        
        prob = TRAFFIC_VOLUME / 3600.0 # Saatteki aracı saniyeye böl
        
        # Kuzey Akışı
        routes.write(f'    <flow id="flow_N_S" type="standard_car" route="N_to_S" begin="0" end="{SIM_DURATION}" probability="{prob * 0.5}"/>\n')
        routes.write(f'    <flow id="flow_N_E" type="standard_car" route="N_to_E" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')
        routes.write(f'    <flow id="flow_N_W" type="standard_car" route="N_to_W" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')

        # Güney Akışı
        routes.write(f'    <flow id="flow_S_N" type="standard_car" route="S_to_N" begin="0" end="{SIM_DURATION}" probability="{prob * 0.5}"/>\n')
        routes.write(f'    <flow id="flow_S_E" type="standard_car" route="S_to_E" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')
        routes.write(f'    <flow id="flow_S_W" type="standard_car" route="S_to_W" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')

        # Doğu Akışı
        routes.write(f'    <flow id="flow_E_W" type="standard_car" route="E_to_W" begin="0" end="{SIM_DURATION}" probability="{prob * 0.5}"/>\n')
        routes.write(f'    <flow id="flow_E_N" type="standard_car" route="E_to_N" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')
        routes.write(f'    <flow id="flow_E_S" type="standard_car" route="E_to_S" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')

        # Batı Akışı
        routes.write(f'    <flow id="flow_W_E" type="standard_car" route="W_to_E" begin="0" end="{SIM_DURATION}" probability="{prob * 0.5}"/>\n')
        routes.write(f'    <flow id="flow_W_N" type="standard_car" route="W_to_N" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')
        routes.write(f'    <flow id="flow_W_S" type="standard_car" route="W_to_S" begin="0" end="{SIM_DURATION}" probability="{prob * 0.25}"/>\n')

        routes.write("</routes>")
    
    print("Başarılı! 'custom_traffic.rou.xml' dosyası oluşturuldu.")

if __name__ == "__main__":
    generate_route_file()