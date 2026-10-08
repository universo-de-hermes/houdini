"""
Detector de Activación — Aplausos + Wake Word
Escucha el micrófono en tiempo real y detecta:
  - 👏 2 aplausos consecutivos (análisis de energía)
  - 🗣️ Palabras clave: "Houdini", "Actívate", "Hola Houdini"
"""
import numpy as np
import sounddevice as sd
import time
import threading
import json
import os
from pathlib import Path

# Config
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.05  # 50ms chunks para detección rápida
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
CLAP_COOLDOWN = 0.8  # segundos máximo entre aplausos
CLAP_ENERGY_THRESHOLD = 0.15  # energía mínima para considerar aplauso
CLAP_WINDOW = 0.5  # ventana para analizar el golpe

class ActivationDetector:
    def __init__(self, on_activate=None):
        self.on_activate = on_activate  # callback: (method, text)
        self.running = False
        self.audio_buffer = []
        self.last_clap_time = 0
        self.clap_count = 0
        self._stream = None
        self._speech_thread = None
        self._last_audio_for_stt = None
        self.paused = False  # Para pausar detección durante TTS
        
        # Para detección de energía
        self._energy_history = []
        self._energy_window_size = int(0.5 / CHUNK_DURATION)  # 0.5s window
        
    def start(self):
        """Inicia la escucha en segundo plano."""
        self.running = True
        
        # Hilo de detección de aplausos (análisis de energía en tiempo real)
        self._clap_thread = threading.Thread(target=self._clap_loop, daemon=True)
        self._clap_thread.start()
        
        # Hilo de wake word (speech-to-text periódico)
        self._speech_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self._speech_thread.start()
        
        print("🎤 Asistente activado — esperando aplausos 👏 o 'Houdini'...")
        
    def pause(self):
        """Pausa la detección (útil durante TTS)."""
        self.paused = True
    
    def resume(self):
        """Reanuda la detección."""
        self.paused = False

    def stop(self):
        self.running = False
        if self._stream:
            self._stream.stop()
            
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback de sounddevice: recibe chunks de audio."""
        if status:
            return
        chunk = indata[:, 0]  # mono
        self._process_chunk(chunk)
        
    def _process_chunk(self, chunk):
        """Analiza un chunk de audio para detectar aplausos."""
        # Energía RMS del chunk
        energy = np.sqrt(np.mean(chunk ** 2))
        self._energy_history.append(energy)
        if len(self._energy_history) > self._energy_window_size:
            self._energy_history.pop(0)
        
        # Detección de aplauso: pico repentino de energía
        if len(self._energy_history) > 10:
            mean_energy = np.mean(self._energy_history[:-5]) + 0.001
            if energy > mean_energy * 10 and energy > CLAP_ENERGY_THRESHOLD:
                self._on_clap_detected()
                
    def _on_clap_detected(self):
        """Un aplauso detectado — contar y verificar si son 2."""
        now = time.time()
        
        if now - self.last_clap_time > CLAP_COOLDOWN * 3:
            # Primer aplauso o reset
            self.clap_count = 1
            self.last_clap_time = now
            print("👏 Aplauso 1...")
        elif now - self.last_clap_time < CLAP_COOLDOWN:
            # Segundo aplauso dentro del tiempo
            self.clap_count += 1
            self.last_clap_time = now
            print("👏 Aplauso 2! Activando...")
            if self.on_activate:
                self.on_activate("clap", "")
            self.clap_count = 0
        else:
            # Muy tarde, resetear
            self.clap_count = 1
            self.last_clap_time = now
            
    def _clap_loop(self):
        """Loop de escucha continua para aplausos."""
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=CHUNK_SIZE,
                callback=self._audio_callback,
                dtype='float32'
            ):
                while self.running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error en audio loop: {e}")
            
    def _wake_word_loop(self):
        """Loop de wake word usando speech_recognition."""
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 800
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.5
        
        # Wake words
        WAKE_WORDS = ["houdini", "actívate", "hola houdini", "activate", "hou",
                         "udini", "dini", "actívame", "oidini", "hoodini",
                         "houdin", "hodini", "audini"]
        
        # Pequeña pausa para que el audio stream se estabilice
        time.sleep(2)
        
        while self.running:
            try:
                with sr.Microphone(sample_rate=16000) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    print("🔊 Escuchando wake word...", end="\r")
                    
                    try:
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    except sr.WaitTimeoutError:
                        continue
                    
                    try:
                        text = recognizer.recognize_google(audio, language="es-CO").lower().strip()
                        
                        if self.paused:
                            continue
                        
                        print(f"\n🗣️ Detectado: {text[:50]}")
                        
                        for wake in WAKE_WORDS:
                            if wake in text or any(w in text for w in ["hudi", "udin", "oudi"]):
                                print(f"🎯 Wake word detectada: '{wake}' en '{text}'")
                                if self.on_activate:
                                    self.on_activate("wake", text)
                                break
                                
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError:
                        pass
                        
            except Exception as e:
                print(f"❌ Error wake word: {e}")
                time.sleep(2)


class VoiceRecorder:
    """Graba la voz después de la activación y la envía al bridge."""
    
    def __init__(self, bridge_url="http://127.0.0.1:9876"):
        self.bridge_url = bridge_url
        self.recording = False
        self._audio_frames = []
        self.detector = None  # Referencia al detector para pausar durante TTS
        self._speaking = False  # Flag para interrumpir TTS con "silencio"
    
    def set_detector(self, detector):
        """Inyecta el detector para pausar/reanudar durante TTS."""
        self.detector = detector
    
    def stop_speaking(self):
        """Detiene la voz en curso."""
        self._speaking = False
        
    def record(self, timeout=8) -> str:
        """
        Graba desde el micrófono hasta silencio o timeout.
        Retorna el texto transcrito.
        """
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 500
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 2.0  # 2s de silencio = fin
        
        print("🎤 Escuchando orden...")
        
        try:
            with sr.Microphone(sample_rate=16000) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                try:
                    audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=12)
                except sr.WaitTimeoutError:
                    return ""
                    
                print("🔄 Procesando...")
                try:
                    text = recognizer.recognize_google(audio, language="es-CO")
                    print(f"📝 Orden: {text}")
                    return text.strip()
                except sr.UnknownValueError:
                    print("❌ No entendí")
                    return ""
                except sr.RequestError:
                    print("❌ Error de conexión STT")
                    return ""
        except Exception as e:
            print(f"❌ Error grabando: {e}")
            return ""
    
    def send_to_bridge(self, text: str) -> dict:
        """Envía texto directamente al bridge (sin pasar por Express/SSE)."""
        import requests
        try:
            resp = requests.post(
                f"{self.bridge_url}/chat",
                json={"message": text, "session_id": "asistente-escritorio"},
                timeout=60
            )
            return resp.json()
        except Exception as e:
            print(f"❌ Error bridge: {e}")
            return {"error": str(e)}
    
    def play_tts_sync(self, text: str):
        """Reproduce TTS de forma BLOQUEANTE (espera a que termine)."""
        import requests
        import tempfile
        import subprocess
        
        # Pausar detección durante TTS
        if self.detector:
            self.detector.pause()
        
        try:
            resp = requests.post(
                f"http://127.0.0.1:9999/api/tts",
                json={"text": text},
                timeout=30
            )
            if resp.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.write(resp.content)
                tmp.close()
                subprocess.call(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                try:
                    os.remove(tmp.name)
                except:
                    pass
                return True
        except Exception as e:
            print(f"❌ Error TTS sync: {e}")
            return False
        finally:
            # Reanudar detección después del TTS
            if self.detector:
                self.detector.resume()
    
    def play_tts(self, text: str):
        """Reproduce TTS de forma INTERRUMPIBLE (silencio la detiene)."""
        import requests
        import tempfile
        import subprocess
        import time
        
        # Pausar detección durante TTS para evitar feedback
        if self.detector:
            self.detector.pause()
        
        # Marcar que estamos hablando
        self._speaking = True
        
        try:
            resp = requests.post(
                f"http://127.0.0.1:9999/api/tts",
                json={"text": text},
                timeout=30
            )
            if resp.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.write(resp.content)
                tmp.close()
                
                # Reproducir en proceso separado para poder matarlo
                proc = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                
                # Esperar pero verificando si debemos parar
                while proc.poll() is None and self._speaking:
                    time.sleep(0.2)
                
                # Si nos pidieron silencio, matar el proceso
                if not self._speaking and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except:
                        pass
                
                try:
                    os.remove(tmp.name)
                except:
                    pass
                return True
        except Exception as e:
            print(f"❌ Error TTS: {e}")
            return False
        finally:
            # Reanudar detección después del TTS
            self._speaking = False
            if self.detector:
                self.detector.resume()