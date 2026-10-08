@echo off
echo ========================================
echo   Houdini Avatar - Servidor Local
echo ========================================
echo.
echo Abriendo servidor en http://localhost:8000
echo Presiona Ctrl+C para detener
echo.
cd /d "%~dp0"
python -m http.server 8000
