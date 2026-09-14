# Endpoints FastAPI para el Frontend y ESP32

import cv2
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.services.yolo_service import YOLOService

router = APIRouter()
yolo_service = YOLOService()

def generate_frames():
    """Generador que procesa los cuadros con YOLO y los transmite en tiempo real"""
    cap = yolo_service.camera_service.get_stream_capture()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue

        # Inferencia con YOLO Pose
        results = yolo_service.model(frame, verbose=False)
        annotated_frame = results[0].plot()

        # Evaluación de postura
        if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            for person in results[0].keypoints.data:
                kpts = person.cpu().numpy()
                if yolo_service._is_sitting(kpts):
                    cv2.putText(annotated_frame, "ESTADO: SENTADO", (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    cv2.putText(annotated_frame, "ESTADO: DE PIE", (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)

        # Codificar el cuadro en formato JPEG para transmisión HTTP
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()

        # Protocolo MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

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
    """Recibe los frames binarios JPEG enviados por la ESP32-S3"""
    await websocket.accept()
    print("🎥 ESP32-S3 Conectada vía WebSocket")
    try:
        while True:
            # Recibe el cuadro en bytes directamente desde la cámara
            data = await websocket.receive_bytes()
            # Aquí puedes enviar los bytes directos a tu yolo_service si es necesario
    except WebSocketDisconnect:
        print("❌ ESP32-S3 Desconectada del WebSocket")
    except Exception as e:
        print(f"⚠️ Error en WebSocket: {e}")
        await websocket.close()