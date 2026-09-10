# YOLOv8 Detección + Pose (Estimación de esqueleto)

import cv2
import time
from ultralytics import YOLO
from app.core.config import settings
from app.services.camera import CameraService

class YOLOService:
    def __init__(self):
        self.model = YOLO("yolov8n-pose.pt")
        self.camera_service = CameraService()

    def _is_sitting(self, keypoints):
        if len(keypoints) < 15:
            return False

        hip_y = (keypoints[11][1] + keypoints[12][1]) / 2
        knee_y = (keypoints[13][1] + keypoints[14][1]) / 2

        vertical_dist = abs(hip_y - knee_y)
        return vertical_dist < 80

    def start_monitoring(self):
        print(f"📡 Conectando a la cámara en {settings.ESP32_STREAM_URL}...")
        cap = self.camera_service.get_stream_capture()

        if not cap.isOpened():
            print(f"❌ No se pudo establecer conexión con el stream: {settings.ESP32_STREAM_URL}")
            print("👉 Verifica que la tarjeta esté encendida y la IP sea correcta en el archivo .env")
            return

        print("✅ Monitor de Postura iniciado. Presiona 'q' en la ventana de video para salir.")
        
        sitting_start_time = None

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ Reintentando lectura de cuadro...")
                time.sleep(0.1)
                continue

            results = self.model(frame, verbose=False)
            annotated_frame = results[0].plot()

            if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
                for person in results[0].keypoints.data:
                    kpts = person.cpu().numpy()
                    if self._is_sitting(kpts):
                        if sitting_start_time is None:
                            sitting_start_time = time.time()
                        
                        siting_duration = int(time.time() - sitting_start_time)
                        cv2.putText(annotated_frame, f"ESTADO: SENTADO ({siting_duration}s)", (20, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    else:
                        sitting_start_time = None
                        cv2.putText(annotated_frame, "ESTADO: DE PIE", (20, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
            else:
                sitting_start_time = None

            cv2.imshow("Guardian AI - Deteccion de Postura Sentado/De Pie", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()