import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

app = FastAPI(
    title="Guardian AI - Industrial Posture Analytics",
    description="Motor Backend para análisis ergónomico en tiempo real con ESP32-S3 y YOLOv8",
    version="1.0.0"
)

# Permitir conexiones desde cualquier origen (necesario para el frontend de React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir las rutas
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    print("🚀 Iniciando Servidor FastAPI en http://0.0.0.0:8000")
    print("📄 Documentación interactiva en http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)