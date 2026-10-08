"""
Houdini - SpotifyAgent (Local Mode)
Controla música local con ffplay y volumen del sistema Windows.
No necesita API de Spotify ni credenciales.
"""
import logging
import os
import random
import subprocess
import threading
import time
import ctypes
from pathlib import Path
from schemas.tools import SpotifyPlayInput, SpotifyControlInput, SpotifyVolumeInput

logger = logging.getLogger("houdini.agents.spotify")

# ── Windows API para volumen ──
if os.name == 'nt':
    try:
        user32 = ctypes.windll.user32
    except AttributeError:
        user32 = None
else:
    user32 = None
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE

def _press_key(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk_code, 0, 2, 0)


class SpotifyAgent:
    """Controla música local del PC: ffplay + volumen sistema."""

    def __init__(self):
        self.current_process = None
        self.is_playing = False
        self.current_track = None
        self._stop_flag = False
        self.last_finished_track = None  # Para saber qué canción terminó
        
        # Escanear música local
        music_dirs = [
            Path.home() / "Music",
            Path("C:/Users/USER/Music"),
        ]
        self.local_tracks = []
        extensions = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]
        for md in music_dirs:
            if md.exists():
                for ext in extensions:
                    self.local_tracks.extend(list(md.glob(f"**/*{ext}")))
        logger.info(f"🎵 {len(self.local_tracks)} canciones locales encontradas")

    async def spotify_play(self, params: SpotifyPlayInput) -> dict:
        """Reproduce música local. Si query, busca canción. Si no, aleatoria."""
        self._stop_flag = False
        
        if not self.local_tracks:
            return {"error": "No hay música local en tu carpeta Music"}

        track = None
        if params.query:
            query_lower = params.query.lower()
            matches = [t for t in self.local_tracks if query_lower in t.stem.lower()]
            if matches:
                track = matches[0]
            else:
                return {"error": f"No encontré '{params.query}' en tu música local"}
        else:
            track = random.choice(self.local_tracks)

        self._stop()
        try:
            cmd = [
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                "-volume", "100", str(track)
            ]
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.current_track = track.name
            self.is_playing = True
            logger.info(f"🎵 Reproduciendo: {track.name}")

            # Monitorear para auto-siguiente
            threading.Thread(target=self._monitor, args=(track,), daemon=True).start()

            return {
                "ok": True,
                "track": track.stem,
                "status": "playing",
            }
        except Exception as e:
            return {"error": str(e)}

    async def spotify_control(self, params: SpotifyControlInput) -> dict:
        """Controla reproducción: pause, next, previous."""
        action = params.action

        if action == "pause":
            self._stop()
            return {"ok": True, "status": "paused"}
        elif action == "play":
            if self.current_track and not self.is_playing:
                # Reanudar con aleatoria
                return await self.spotify_play(SpotifyPlayInput(query=None))
            return {"ok": True, "status": "playing"}
        elif action == "next":
            return await self.spotify_play(SpotifyPlayInput(query=None))
        elif action == "previous":
            return await self.spotify_play(SpotifyPlayInput(query=None))
        else:
            return {"error": f"Acción no soportada: {action}"}

    async def spotify_volume(self, params: SpotifyVolumeInput) -> dict:
        """Ajusta volumen del sistema Windows."""
        current = params.volume_percent
        target = current
        
        # La API de volumen de Windows necesita subir/bajar
        # Calculamos diferencia
        try:
            # Obtener volumen actual
            steps = target // 2  # ~2% por step
            if target > 50:
                _press_key(VK_VOLUME_UP)
                time.sleep(0.01)
            elif target < 50 and target > 0:
                _press_key(VK_VOLUME_DOWN)
                time.sleep(0.01)
            
            return {"ok": True, "volume": target}
        except Exception as e:
            return {"error": str(e)}

    def _stop(self):
        """Detiene reproducción actual."""
        self._stop_flag = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass
            self.current_process = None
        self.is_playing = False

    def _monitor(self, track):
        """Cuando termina una canción, guardamos el nombre."""
        if self.current_process:
            try:
                self.current_process.wait()
                self.is_playing = False
                self.last_finished_track = track.name
                print(f"⏹️ Canción terminada: {track.name}")
                if not self._stop_flag:
                    time.sleep(1)
            except:
                pass