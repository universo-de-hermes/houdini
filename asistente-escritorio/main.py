"""
Houdini Desktop — Asistente Always-On
Escucha 24/7, detecta aplausos 👏 y wake word "Houdini",
ejecuta rutina matutina, y procesa órdenes por voz.

Uso: python main.py
"""
import sys
import os
import time
import threading
import signal
import subprocess

# ── Solo una instancia ──
# Matar cualquier otra instancia de este mismo script
_pid = os.getpid()
try:
    result = subprocess.run(
        ['ps', 'aux'], capture_output=True, text=True, timeout=5
    )
    for line in result.stdout.split('\n'):
        if 'python main.py' in line and str(_pid) not in line:
            parts = line.split()
            if len(parts) > 1:
                try:
                    old_pid = int(parts[1])
                    os.kill(old_pid, 9)
                    print(f"🧹 Instancia anterior (PID {old_pid}) eliminada")
                except:
                    pass
except:
    pass

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detector import ActivationDetector, VoiceRecorder
from assistant import HoudiniAssistant
from music import MusicPlayer
from power import PowerManager


def main():
    print("""
    ╔═══════════════════════════════════════╗
    ║     🎩 HOUDINI ASISTENTE DE ESCRITORIO  ║
    ║     Siempre activo · Local · Privado    ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Verificar que los servicios estén corriendo
    _check_services()
    
    # Inicializar componentes
    recorder = VoiceRecorder()
    assistant = HoudiniAssistant()
    music = MusicPlayer(assistant.config)
    power = PowerManager()
    
    assistant.set_recorder(recorder)
    assistant.set_music_player(music)
    
    # Activar modo siempre despierto (evita suspensión)
    power.enable()
    print("⚡ Suspensión del PC desactivada mientras el asistente corre")
    print("   La pantalla puede apagarse, pero el PC no dormirá")
    print("   El micrófono seguirá escuchando 24/7")
    
    # Crear detector con callback de activación
    detector = ActivationDetector(on_activate=assistant.on_activation)
    
    # Conectar detector al recorder (para pausar durante TTS)
    recorder.set_detector(detector)
    
    # Manejar Ctrl+C gracefulmente
    def shutdown(sig, frame):
        print("\n\n🛑 Deteniendo asistente...")
        detector.stop()
        music.stop()
        assistant.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # Iniciar detector (corre en segundo plano)
    detector.start()
    
    # Mantener vivo el proceso principal
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


def _check_services():
    """Verifica que el bridge y API estén funcionando."""
    import urllib.request
    import json
    
    services = [
        ("Bridge Houdini", "http://127.0.0.1:9876/health"),
        ("API Express", "http://127.0.0.1:9999/api/config"),
    ]
    
    all_ok = True
    for name, url in services:
        try:
            resp = urllib.request.urlopen(url, timeout=3)
            if resp.status == 200:
                print(f"  ✅ {name}: OK")
            else:
                print(f"  ⚠️ {name}: respuesta {resp.status}")
                all_ok = False
        except Exception as e:
            print(f"  ❌ {name}: No disponible - {e}")
            print(f"     Asegúrate de que el bridge y API estén corriendo.")
            all_ok = False
    
    if not all_ok:
        print("\n⚠️ Algunos servicios no están disponibles.")
        print("   Ejecuta en otra terminal:")
        print("   cd server && python houdini-bridge.py")
        print("   node server/index.js")
        print()
    
    return all_ok


if __name__ == "__main__":
    main()