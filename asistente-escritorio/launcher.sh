#!/usr/bin/env bash
# 🎩 Houdini Desktop Assistant — Launcher
# Arranca: Bridge Python + Express API + Asistente de Escritorio

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "╔═══════════════════════════════════════╗"
echo "║  🎩 HOUDINI — Asistente Always-On     ║"
echo "║  Iniciando servicios...               ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# 1. Bridge Python
echo "[1/3] 🐍 Iniciando Bridge Houdini..."
lsof -ti:9876 2>/dev/null | xargs kill -9 2>/dev/null
cd "$PROJECT_DIR"/server
python houdini-bridge.py &
BRIDGE_PID=$!
sleep 3

# 2. Express API
echo "[2/3] 🖥️ Iniciando API Express..."
lsof -ti:9999 2>/dev/null | xargs kill -9 2>/dev/null
cd "$PROJECT_DIR"
node server/index.js &
EXPRESS_PID=$!
sleep 2

# 3. Asistente de Escritorio
echo "[3/3] 🎤 Iniciando Asistente de Voz..."
cd "$SCRIPT_DIR"
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
python main.py &
DESKTOP_PID=$!

echo ""
echo "✅ Todos los servicios iniciados!"
echo "   Bridge:  :9876"
echo "   API:     :9999"
echo "   Web UI:  :8001 (Vite)"
echo "   Voz:     Asistente activo 👏🎤"
echo ""
echo "Presiona Ctrl+C para detener todo"

# Trap para detener todo
trap "echo ''; echo '🛑 Deteniendo...'; kill $BRIDGE_PID $EXPRESS_PID $DESKTOP_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Mantener vivo
wait