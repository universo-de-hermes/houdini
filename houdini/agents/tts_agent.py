"""
Houdini - TTS Agent
Sub-agente para texto-a-voz usando edge-tts con voz "Salome" (es-CO-SalomeNeural).
"""
import logging
import asyncio
import os
import tempfile
from datetime import datetime
from schemas.tools import SpeakInput

logger = logging.getLogger("houdini.agents.tts")


class TTSAgent:
    """Sub-agente para texto-a-voz con voz Salome."""

    def __init__(self, voice: str = "es-CO-SalomeNeural", rate: str = "+0%", volume: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.output_dir = os.path.join(tempfile.gettempdir(), "houdini_tts")
        os.makedirs(self.output_dir, exist_ok=True)

    async def speak(self, params: SpeakInput) -> dict:
        """Convierte texto a voz y guarda como MP3."""
        try:
            import edge_tts
        except ImportError:
            return {"error": "edge-tts no instalado. Ejecuta: pip install edge-tts"}

        try:
            voice = params.voice or self.voice
            rate = params.rate or self.rate
            volume = params.volume or self.volume

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"tts_{timestamp}.mp3")

            communicate = edge_tts.Communicate(
                text=params.text,
                voice=voice,
                rate=rate,
                volume=volume,
            )
            await communicate.save(output_path)

            logger.info(f"TTS generado: {output_path} (voz={voice})")
            return {
                "audio_path": output_path,
                "voice": voice,
                "status": "ok",
            }
        except Exception as e:
            logger.error(f"Error TTS: {e}")
            return {"error": str(e)}

    async def speak_and_play(self, text: str, voice: str | None = None) -> dict:
        """Convierte a voz y reproduce localmente (modo escritorio)."""
        result = await self.speak(SpeakInput(
            text=text,
            voice=voice or self.voice,
        ))
        if "error" in result:
            return result

        # Reproducir
        audio_path = result["audio_path"]
        try:
            if os.name == "nt":  # Windows
                os.system(f'start "" "{audio_path}"')
            else:  # Linux/Mac
                os.system(f'mpg123 "{audio_path}" 2>/dev/null || aplay "{audio_path}" 2>/dev/null &')
            return {**result, "played": True}
        except Exception as e:
            return {**result, "played": False, "play_error": str(e)}

    def list_available_voices(self) -> list[str]:
        """Retorna voces salome-related disponibles."""
        return [
            "es-CO-SalomeNeural",     # Salome (Colombia) - recomendada
            "es-ES-ElviraNeural",      # Elvira (España)
            "es-MX-DaliaNeural",       # Dalia (Mexico)
            "es-AR-ElenaNeural",       # Elena (Argentina)
        ]
