"""
Power Manager — Evita suspensión del PC, permite apagar pantalla.
Usa SetThreadExecutionState para mantener el sistema activo.
"""
import ctypes
import time

# ES_CONTINUOUS = 0x80000000
# ES_SYSTEM_REQUIRED = 0x00000001
# ES_DISPLAY_REQUIRED = 0x00000002
# ES_AWAYMODE_REQUIRED = 0x00000040

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

kernel32 = ctypes.windll.kernel32
SetThreadExecutionState = kernel32.SetThreadExecutionState


class PowerManager:
    """Mantiene el PC despierto (suspensión desactivada) pero permite apagar pantalla."""

    def __init__(self):
        self._active = False

    def enable(self):
        """
        Evita que el PC entre en suspensión.
        La pantalla puede apagarse por energía (Windows).
        El sistema NO se suspenderá mientras esto esté activo.
        """
        SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        self._active = True
        print("⚡ Modo siempre activo: suspensión desactivada")

    def enable_with_display(self):
        """
        Evita suspensión Y evita que la pantalla se apague.
        """
        SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        self._active = True
        print("⚡ Modo máximo: suspensión + pantalla siempre encendida")

    def disable(self):
        """Restaura el comportamiento normal de energía."""
        SetThreadExecutionState(ES_CONTINUOUS)
        self._active = False
        print("⚡ Comportamiento de energía restaurado")

    def is_active(self):
        return self._active


# Probar si funciona
if __name__ == "__main__":
    pm = PowerManager()
    pm.enable()
    print("✅ Modo siempre activo. El PC no se suspenderá.")
    print("   Presiona Ctrl+C para desactivar.")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        pm.disable()
        print("✅ Modo desactivado.")