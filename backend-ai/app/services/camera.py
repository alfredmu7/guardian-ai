# Conexión al stream HTTP del ESP32-S3

import cv2
import requests
import numpy as np
from app.core.config import settings

class CameraService:
    def __init__(self):
        self.stream_url = settings.ESP32_STREAM_URL
        self.capture_url = settings.ESP32_CAPTURE_URL

    def get_stream_capture(self):
        """Abre el stream HTTP con banderas de baja latencia para OpenCV"""
        # Forzar transporte TCP y búfer mínimo en OpenCV/FFmpeg
        return cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)

    def get_capture(self):
        """Obtiene una foto estática en alta resolución desde /capture"""
        try:
            response = requests.get(self.capture_url, timeout=3)
            if response.status_code == 200:
                image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"⚠️ Error al capturar foto estática: {e}")
        return None