Set WshShell = CreateObject("WScript.Shell")
' Ejecuta el servidor FastAPI usando el entorno virtual en modo invisible (0)
Set FileSystem = CreateObject("Scripting.FileSystemObject")
BackendDirectory = FileSystem.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c ""cd /d " & BackendDirectory & " && venv\Scripts\pythonw.exe -m uvicorn main:app --host 0.0.0.0 --port 8000""", 0, False