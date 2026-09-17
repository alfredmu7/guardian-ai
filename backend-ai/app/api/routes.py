import os
os.environ["OPENCV_LOG_LEVEL"] = "OFF"

import cv2
import asyncio
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse, JSONResponse
from app.services.yolo_service import YOLOService
from app.services.face_service import FaceRecognitionService

router = APIRouter()
yolo_service = YOLOService()
face_service = FaceRecognitionService(known_image_path="assets/alfred.jpg", person_name="Alfred M")

latest_raw_frame = None
latest_annotated_frame = None
is_processing = False
frame_counter = 0


def process_yolo_frame(frame: np.ndarray) -> np.ndarray:
    """Procesa el frame con YOLOv8 Pose e InsightFace aplicando optimizaciones."""
    try:
        annotated_frame = frame.copy()
        h, w = frame.shape[:2]

        # Reducir resolución para la inferencia rápida de YOLO
        small_frame = cv2.resize(frame, (320, 240))
        
        # 1. Inferencia YOLOv8 Pose
        results = yolo_service.model(small_frame, verbose=False, imgsz=320, conf=0.5)
        
        if len(results) > 0 and results[0].keypoints is not None:
            # Re-escalar y dibujar las anotaciones de YOLO sobre el frame original
            annotated_small = results[0].plot()
            annotated_frame = cv2.resize(annotated_small, (w, h))

            # Evaluar estado postural (sentado / de pie)
            if len(results[0].keypoints.data) > 0:
                for person in results[0].keypoints.data:
                    kpts = person.cpu().numpy()
                    is_sitting = yolo_service._is_sitting(kpts)
                    status_text = "SENTADO" if is_sitting else "DE PIE"
                    color_status = (0, 255, 255) if is_sitting else (255, 255, 0)
                    cv2.putText(annotated_frame, f"Estado: {status_text}", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_status, 2)

        # 2. Reconocimiento Facial (InsightFace)
        face_matches = face_service.identify_in_frame(frame, threshold=0.38)
        for bbox, name, sim in face_matches:
            x1, y1, x2, y2 = bbox
            color = (0, 255, 0) if name != "Desconocido" else (0, 0, 255)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{name} ({sim:.2f})"
            cv2.putText(annotated_frame, label, (x1, max(25, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        return annotated_frame
    except Exception as e:
        print(f"⚠️ Error procesando frame: {e}")
        return frame


async def yolo_worker():
    """Worker asíncrono para ejecutar la inferencia en segundo plano sin congelar el socket."""
    global latest_raw_frame, latest_annotated_frame, is_processing
    while True:
        if latest_raw_frame is not None and not is_processing:
            is_processing = True
            try:
                frame_to_process = latest_raw_frame.copy()
                annotated = await asyncio.to_thread(process_yolo_frame, frame_to_process)
                latest_annotated_frame = annotated
            finally:
                is_processing = False
        
        await asyncio.sleep(0.01)


@router.on_event("startup")
async def startup_event():
    asyncio.create_task(yolo_worker())


@router.get("/capture-reference")
async def capture_reference():
    global latest_raw_frame
    if latest_raw_frame is None:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No se ha recibido ningún cuadro desde la ESP32-S3"})
    
    success = face_service.save_reference_from_frame(latest_raw_frame)
    if success:
        return {"status": "ok", "message": "Rostro registrado correctamente en assets/alfred.jpg"}
    else:
        return JSONResponse(status_code=422, content={"status": "error", "message": "No se detectó un rostro claro en el cuadro actual"})


@router.get("/video-feed")
async def video_feed(request: Request):
    """Transmisión en vivo MJPEG fluida."""
    async def frame_generator():
        global latest_annotated_frame, latest_raw_frame
        while True:
            if await request.is_disconnected():
                break

            # Mostrar frame procesado si existe; si no, mostrar raw frame
            frame_display = latest_annotated_frame if latest_annotated_frame is not None else latest_raw_frame

            if frame_display is not None:
                # Comprimir a JPEG con calidad 60 para reducir latencia de red
                ret, buffer = cv2.imencode('.jpg', frame_display, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            await asyncio.sleep(0.03)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/health")
def health_check():
    return {"status": "ok", "environment": "local"}


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """Recepción de video binario desde la ESP32-S3 con descarte de paquetes anticuados."""
    global latest_raw_frame, frame_counter
    await websocket.accept()
    print("🎥 ESP32-S3 Conectada al WebSocket Local")

    try:
        while True:
            data = await websocket.receive_bytes()
            if not data or len(data) < 500:
                continue

            # Frame Skipping: procesar solo 1 de cada 2 cuadros recibidos para evitar acumulación
            frame_counter += 1
            if frame_counter % 2 != 0:
                continue

            np_arr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                latest_raw_frame = frame

    except WebSocketDisconnect:
        print("❌ ESP32-S3 Desconectada del WebSocket Local")
    except Exception as e:
        print(f"⚠️ Error en WebSocket: {e}")
    finally:
        print("🔒 Conexión WebSocket cerrada")