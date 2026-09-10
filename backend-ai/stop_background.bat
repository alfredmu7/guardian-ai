@echo off
echo 🛑 Deteniendo el servidor FastAPI de Guardian AI en segundo plano...
taskkill /F /IM pythonw.exe /T >nul 2>&1
echo ✅ Servidor detenido correctamente.
pause