# Endpoints FastAPI para el Frontend y ESP32-S3

import cv2
import time
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.services.yolo_service import YOLOService

router = APIRouter()
yolo_service = YOLOService()

# Variable global o de módulo para compartir el último frame procesado de la ESP32 con el video feed web
latest_annotated_frame = None

def generate_frames():
    """Generador que transmite el cuadro procesado en tiempo real mediante MJPEG"""
    global latest_annotated_frame
    
    # Intento de fallback a cámara local si no hay stream activo desde la ESP32
    cap = None

    while True:
        if latest_annotated_frame is not None:
            frame_to_send = latest_annotated_frame.copy()
        else:
            if cap is None:
                cap = yolo_service.camera_service.get_stream_capture()
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Inferencia de reserva con cámara local
            results = yolo_service.model(frame, verbose=False)
            frame_to_send = results[0].plot()

        # Codificar el cuadro en formato JPEG
        _, buffer = cv2.imencode('.jpg', frame_to_send)
        frame_bytes = buffer.tobytes()

        # Protocolo MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.03) # ~30 FPS para la transmisión HTTP

@router.get("/video-feed")
def video_feed():
    """Endpoint para transmitir el video procesado a cualquier cliente web"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/health")
def health_check():
    """Endpoint de diagnóstico para saber si la API está en línea"""
    return {"status": "ok", "service": "Guardian AI Engine"}

# --- ENDPOINT WEBSOCKET PARA ESP32-S3 ---
@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """Recibe los frames binarios JPEG enviados por la ESP32-S3 y realiza inferencia YOLO"""
    global latest_annotated_frame
    await websocket.accept()
    print("🎥 ESP32-S3 Conectada vía WebSocket")
    
    try:
        while True:
            # Recibir los bytes JPEG de la imagen
            data = await websocket.receive_bytes()
            if not data:
                continue

            # Decodificar el buffer de bytes en una matriz de imagen OpenCV
            np_arr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                # Inferencia con YOLO Pose
                results = yolo_service.model(frame, verbose=False)
                annotated_frame = results[0].plot()

                # Evaluación de postura ergonómica
                if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
                    for person in results[0].keypoints.data:
                        kpts = person.cpu().numpy()
                        if yolo_service._is_sitting(kpts):
                            cv2.putText(annotated_frame, "ESTADO: SENTADO", (20, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        else:
                            cv2.putText(annotated_frame, "ESTADO: DE PIE", (20, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)

                # Actualizar el frame global para el stream web
                latest_annotated_frame = annotated_frame

            # Confirmación explícita (ACK) para evitar que la conexión sea cerrada por timeout
            await websocket.send_text("ACK")

    except WebSocketDisconnect:
        print("❌ ESP32-S3 Desconectada del WebSocket")
    except Exception as e:
        print(f"⚠️ Error en WebSocket: {e}")
    finally:
        print("🔒 Conexión con la ESP32-S3 cerrada")