Set WshShell = CreateObject("WScript.Shell")
' Ejecuta el servidor FastAPI usando el entorno virtual en modo invisible (0)
WshShell.Run "cmd /c ""cd /d " & WshShell.CurrentDirectory & " && venv\Scripts\pythonw.exe -m uvicorn main:app --host 0.0.0.0 --port 8000""", 0, False