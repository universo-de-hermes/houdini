@echo off
chcp 65001 >nul
echo.
echo  ╔═══════════════════════════════════════╗
echo  ║  ^🎩 HOUDINI — Asistente Always-On     ║
echo  ║  Iniciando servicios...               ║
echo  ╚═══════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/3] 🐍 Iniciando Bridge Houdini...
start "Houdini Bridge" python ..\server\houdini-bridge.py
timeout /t 4 /nobreak >nul

echo [2/3] 🖥️ Iniciando API Express...
start "Houdini API" node ..\server\index.js
timeout /t 3 /nobreak >nul

echo [3/3] 🎤 Iniciando Asistente de Escritorio...
start "Houdini Desktop" cmd /c "call .venv\Scripts\activate.bat && python main.py"

echo.
echo  ^✅ Todos los servicios iniciados!
echo     Bridge:  :9876
echo     API:     :9999
echo     Web UI:  :8001 (Vite)
echo     Voz:     Asistente activo ^👏^🎤
echo.
echo  Presiona cualquier tecla para abrir la web
pause >nul
start http://localhost:8001/
echo.