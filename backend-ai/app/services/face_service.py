import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis

class FaceRecognitionService:
    def __init__(self, known_image_path: str = "assets/alfred.jpg", person_name: str = "Alfred M"):
        self.person_name = person_name
        self.known_image_path = known_image_path
        self.known_embedding = None
        
        # Inicializar el modelo liviano 'buffalo_s' con motor ONNX en CPU
        self.app = FaceAnalysis(name="buffalo_s", providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(320, 320))
        
        if os.path.exists(self.known_image_path):
            self.load_known_face(self.known_image_path)
        else:
            print(f"⚠️ [FaceService] Imagen de referencia no encontrada en: {self.known_image_path}")

    def load_known_face(self, image_path: str):
        """Carga la foto de referencia y extrae el vector de características (embedding)."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                print(f"⚠️ [FaceService] No se pudo leer la imagen en {image_path}")
                return
            
            faces = self.app.get(img)
            if len(faces) > 0:
                largest_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
                self.known_embedding = largest_face.embedding
                print(f"✅ [FaceService] Rostro de '{self.person_name}' cargado con éxito desde {image_path}.")
            else:
                print(f"⚠️ [FaceService] No se detectó ningún rostro en la imagen {image_path}.")
        except Exception as e:
            print(f"⚠️ [FaceService] Error cargando el rostro conocido: {e}")

    def save_reference_from_frame(self, frame: np.ndarray) -> bool:
        """Guarda el fotograma directo de la ESP32-S3 como la nueva foto de referencia."""
        try:
            os.makedirs(os.path.dirname(self.known_image_path), exist_ok=True)
            faces = self.app.get(frame)
            if len(faces) == 0:
                print("⚠️ [FaceService] No se detectó rostro en el fotograma recibido para capturar de referencia.")
                return False

            cv2.imwrite(self.known_image_path, frame)
            largest_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
            self.known_embedding = largest_face.embedding
            print(f"📸 [FaceService] ¡Nueva foto de referencia guardada con éxito en {self.known_image_path}!")
            return True
        except Exception as e:
            print(f"⚠️ [FaceService] Error guardando foto de referencia: {e}")
            return False

    def identify_in_frame(self, frame: np.ndarray, threshold: float = 0.38) -> list:
        """Detecta y reconoce rostros evaluando el fotograma completo."""
        if self.known_embedding is None or frame.size == 0:
            return []

        results = []
        faces = self.app.get(frame)

        for face in faces:
            bbox = face.bbox.astype(int)
            # Cálculo de la similitud del coseno usando np.linalg.norm correctamente
            sim = np.dot(self.known_embedding, face.embedding) / (
                np.linalg.norm(self.known_embedding) * np.linalg.norm(face.embedding)
            )
            name = self.person_name if sim > threshold else "Desconocido"
            results.append((bbox, name, float(sim)))

        return results

    def identify_face(self, crop_frame: np.ndarray) -> str:
        matches = self.identify_in_frame(crop_frame)
        if matches:
            return matches[0][1]
        return "Desconocido"

    def match_face(self, crop_frame: np.ndarray) -> str:
        return self.identify_face(crop_frame)