import cv2
from ultralytics import YOLO
import os

class TrafficVision:
    def __init__(self, model_path, video_source):
        """
        Görüntü işleme sistemini başlatır.
        """
        print(f"--- Vision Sistemi Başlatılıyor ---")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model bulunamadı: {model_path}")
        
        if not os.path.exists(video_source):
            raise FileNotFoundError(f"Video bulunamadı: {video_source}")

        # YOLO modelini yükle
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(video_source)
        
    def get_vehicle_count(self):
        """
        Videodan sıradaki kareyi okur ve araç sayısını döndürür.
        Return: (araç_sayısı, frame_görüntüsü)
        Eğer video biterse: (-1, None) döner.
        """
        ret, frame = self.cap.read()
        if not ret:
            return -1, None # Video bitti

        # Tahmin yap (conf=0.25)
        # verbose=False: Terminali spamlamaması için
        results = self.model.predict(frame, conf=0.25, verbose=False)
        result = results[0]
        
        # Tespit edilen kutu sayısı = Araç Sayısı
        vehicle_count = len(result.boxes)
        
        # Çizilmiş kareyi de oluştur (gerekirse göstermek için)
        annotated_frame = result.plot()
        
        return vehicle_count, annotated_frame

    def release(self):
        self.cap.release()