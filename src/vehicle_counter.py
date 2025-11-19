import cv2
from ultralytics import YOLO
import os

def get_project_paths():
    """
    Dosya yapısına göre dinamik yolları belirler.
    src/traffic_controller.py dosyasının konumuna göre hareket eder.
    """
    # Şu anki dosyanın (traffic_controller.py) bulunduğu klasör (src)
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    # Projenin ana dizini (Smart-Traffic-Light-SUMO-RL)
    ROOT_DIR = os.path.dirname(CURRENT_DIR)
    
    paths = {
        "model": os.path.join(ROOT_DIR, "models", "best.pt"),
        "image": os.path.join(ROOT_DIR, "data", "test_data", "test_frame.jpg"),
        "video": os.path.join(ROOT_DIR, "data", "test_data", "test_video.mp4")
    }
    return paths

def count_vehicles_in_image(model, image_path):
    print(f"\n--- Görüntü Analizi Başlıyor: {os.path.basename(image_path)} ---")
    
    if not os.path.exists(image_path):
        print("HATA: Görüntü dosyası bulunamadı!")
        return

    image = cv2.imread(image_path)
    
    # Tahmin yap (conf=0.25 güven eşiği)
    results = model.predict(image, conf=0.25)
    
    # Sonuçları al
    result = results[0]
    detected_count = len(result.boxes)
    
    print(f"Tespit Edilen Araç Sayısı: {detected_count}")
    
    # Kutuları çiz ve göster
    annotated_frame = result.plot()
    
    # Sonucu ekranda göster
    cv2.imshow("Resim Analizi", annotated_frame)
    cv2.waitKey(0) # Bir tuşa basana kadar bekle
    cv2.destroyAllWindows()

def count_vehicles_in_video(model, video_path):
    print(f"\n--- Video Analizi Başlıyor: {os.path.basename(video_path)} ---")
    
    if not os.path.exists(video_path):
        print("HATA: Video dosyası bulunamadı!")
        return

    cap = cv2.VideoCapture(video_path)
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Tahmin yap
        results = model.predict(frame, conf=0.25, verbose=False) # verbose=False terminali temiz tutar
        result = results[0]
        
        # Sayım yap
        vehicle_count = len(result.boxes)
        
        # Görselleştirme
        annotated_frame = result.plot()
        
        # Ekrana yazı yazdır
        cv2.putText(annotated_frame, f"Arac Sayisi: {vehicle_count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Video Analizi (Cikmak icin 'q' basin)", annotated_frame)

        # 'q' tuşuna basılırsa çık
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    paths = get_project_paths()
    
    # Model dosyasının varlığını kontrol et
    if os.path.exists(paths["model"]):
        print("Model yükleniyor...")
        # YOLO modelini yükle
        model = YOLO(paths["model"])
        
        # 1. Resmi Analiz Et
        count_vehicles_in_image(model, paths["image"])
        
        # 2. Videoyu Analiz Et
        count_vehicles_in_video(model, paths["video"])
        
    else:
        print(f"HATA: Model dosyası bulunamadı: {paths['model']}")
        print("Lütfen 'models' klasörüne 'best.pt' dosyasını koyduğunuzdan emin olun.")