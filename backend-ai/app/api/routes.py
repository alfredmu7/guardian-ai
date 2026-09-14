# app/api/routes.py

import cv2
import time
import asyncio
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.services.yolo_service import YOLOService

router = APIRouter()
yolo_service = YOLOService()

latest_annotated_frame = None

def process_yolo_frame(frame):
    """Procesamiento de inferencia aislado."""
    try:
        results = yolo_service.model(frame, verbose=False)
        annotated_frame = results[0].plot()

        if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            for person in results[0].keypoints.data:
                kpts = person.cpu().numpy()
                if yolo_service._is_sitting(kpts):
                    cv2.putText(annotated_frame, "ESTADO: SENTADO", (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    cv2.putText(annotated_frame, "ESTADO: DE PIE", (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
        return annotated_frame
    except Exception as e:
        print(f"⚠️ Error procesando frame en YOLO: {e}")
        return frame


async def generate_frames():
    """Generador para el endpoint MJPEG."""
    global latest_annotated_frame

    while True:
        if latest_annotated_frame is not None:
            frame_to_send = latest_annotated_frame.copy()
            ret, buffer = cv2.imencode('.jpg', frame_to_send)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            await asyncio.sleep(0.1)
            continue

        await asyncio.sleep(0.05)


@router.get("/video-feed")
async def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "Guardian AI Engine"}


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    global latest_annotated_frame
    await websocket.accept()
    print("🎥 ESP32-S3 Conectada vía WebSocket")

    try:
        while True:
            data = await websocket.receive_bytes()
            if not data or len(data) < 100:  # Ignorar paquetes incompletos o corruptos
                continue

            np_arr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                # Ejecución asíncrona de inferencia
                annotated_frame = await asyncio.to_thread(process_yolo_frame, frame)
                latest_annotated_frame = annotated_frame

    except WebSocketDisconnect:
        print("❌ ESP32-S3 Desconectada del WebSocket")
    except Exception as e:
        print(f"⚠️ Error en WebSocket: {e}")
    finally:
        print("🔒 Conexión WebSocket cerrada")