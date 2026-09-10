# Configuraciones globales (Variables de entorno, Gemini API)import os
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ESP32_STREAM_URL: str = os.getenv("ESP32_STREAM_URL", "http://172.20.10.3/stream")
    ESP32_CAPTURE_URL: str = os.getenv("ESP32_CAPTURE_URL", "http://172.20.10.3/capture")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()