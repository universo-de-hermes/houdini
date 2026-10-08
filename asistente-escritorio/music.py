"""
Reproductor de Música — Local
Reproduce música local, controla volumen del sistema Windows,
y simula teclas multimedia (Play/Pause, Next, Previous)
que funcionan con Spotify, YouTube, VLC y cualquier app.
"""
import os
import random
import threading
import subprocess
import time
import ctypes
from pathlib import Path
from ctypes import wintypes

# ── Windows API para volumen del sistema ──
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except:
    PYCAW_AVAILABLE = False

# ── Windows API para teclas multimedia ──
# Simula pulsaciones de teclas multimedia (Play/Pause, Next, Previous)
user32 = ctypes.windll.user32
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_MUTE = 0xAD

def _press_key(vk_code):
    """Simula una pulsación de tecla virtual."""
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP

def system_volume_up(steps=5):
    """Sube volumen del sistema usando tecla multimedia."""
    for _ in range(steps):
        _press_key(VK_VOLUME_UP)
        time.sleep(0.02)

def system_volume_down(steps=5):
    """Baja volumen del sistema usando tecla multimedia."""
    for _ in range(steps):
        _press_key(VK_VOLUME_DOWN)
        time.sleep(0.02)

def media_play_pause():
    """Play/Pause multimedia."""
    _press_key(VK_MEDIA_PLAY_PAUSE)

def media_next():
    """Siguiente pista multimedia."""
    _press_key(VK_MEDIA_NEXT_TRACK)

def media_previous():
    """Pista anterior multimedia."""
    _press_key(VK_MEDIA_PREV_TRACK)

def get_system_volume():
    """Obtiene el volumen actual del sistema (0-100)."""
    try:
        if PYCAW_AVAILABLE:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            return int(volume.GetMasterVolumeLevelScalar() * 100)
    except:
        pass
    return 50


class MusicPlayer:
    def __init__(self, config):
        self.config = config
        self.current_process = None
        self.is_playing = False
        self.current_track = None
        self._manually_stopped = False
        self.last_played = None
        
        # Buscar archivos de música locales
        self.music_dir = Path(config.get("musica_local", str(Path.home() / "Music")))
        self.local_tracks = []
        self._scan_local_music()
    
    def _scan_local_music(self):
        """Escanea la carpeta de música local."""
        extensions = [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma"]
        if self.music_dir.exists():
            for ext in extensions:
                self.local_tracks.extend(list(self.music_dir.glob(f"**/*{ext}")))
            print(f"🎵 {len(self.local_tracks)} canciones locales encontradas")
        else:
            print(f"⚠️ Carpeta de música no encontrada: {self.music_dir}")
    
    def play_random(self):
        """Reproduce una canción aleatoria local."""
        if not self.local_tracks:
            return False
        self._manually_stopped = False
        self.last_played = None
        track = random.choice(self.local_tracks)
        self._play_file(track)
        return True
    
    def play_file(self, path):
        """Reproduce un archivo específico."""
        self._manually_stopped = False
        self.last_played = path.name
        self._play_file(path)
        return True
    
    def play_track(self, query):
            """Busca y reproduce una canción por nombre."""
            query_lower = query.lower()
            matches = [t for t in self.local_tracks if query_lower in t.stem.lower()]
            if matches:
                self._manually_stopped = False
                self.last_played = matches[0].name
                self._play_file(matches[0])
                return True
            return False
    
    def stop(self):
        """Detiene la reproducción local."""
        self._manually_stopped = True
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process = None
            except:
                pass
        self.is_playing = False
        print("⏹️ Música detenida")
    
    def next(self):
        """Siguiente canción local."""
        self.stop()
        time.sleep(0.2)
        self.play_random()
    
    def volume_up(self):
        """Sube volumen del sistema."""
        system_volume_up(5)
        vol = get_system_volume()
        print(f"🔊 Volumen: {vol}%")
    
    def volume_down(self):
        """Baja volumen del sistema."""
        system_volume_down(5)
        vol = get_system_volume()
        print(f"🔉 Volumen: {vol}%")
    
    def state(self):
        """Devuelve el estado actual."""
        vol = get_system_volume()
        return {
            "is_playing": self.is_playing,
            "current_track": self.current_track,
            "volume": vol,
        }
    
    def _play_file(self, path):
        """Reproduce un archivo local con ffplay."""
        self.stop()
        try:
            cmd = [
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                "-volume", "100",
                str(path)
            ]
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.current_track = path.name
            self.is_playing = True
            print(f"🎵 Reproduciendo: {path.name}")
            
            threading.Thread(target=self._monitor_process, daemon=True).start()
            
        except Exception as e:
            print(f"❌ Error reproduciendo: {e}")
    
    def _monitor_process(self):
        """Espera que termine y reproduce otra."""
        if self.current_process:
            try:
                self.current_process.wait()
                self.is_playing = False
                if not self._manually_stopped:
                    time.sleep(1)
                    self.play_random()
            except:
                pass