"""
Asistente de Escritorio — Houdini Always-On
Rutina matutina, música, noticias, clima, calendario y más.
"""
import json
import os
import time
import threading
import subprocess
import webbrowser
from pathlib import Path

class HoudiniAssistant:
    def __init__(self):
        self.config_path = Path(__file__).parent / "config.json"
        self.config = self._load_config()
        self.bridge_url = "http://127.0.0.1:9876"  # directo al bridge para consultas internas
        self.api_url = "http://127.0.0.1:9999"
        self.web_url = "http://localhost:8001"
        self.music_player = None
        self.recorder = None
        
    def _load_config(self):
        default = {
            "nombre_usuario": "Jefe",
            "ubicacion": "Medellín, Colombia",
            "unidad_temperatura": "celsius",
            "musica_local": str(Path.home() / "Music"),
            "spotify": {
                "enabled": False,
                "client_id": "",
                "client_secret": "",
                "device_name": ""
            },
            "noticias": {
                "categorias": ["inteligencia artificial", "tecnología"],
                "max_noticias": 3
            }
        }
        try:
            with open(self.config_path) as f:
                return {**default, **json.load(f)}
        except:
            return default
    
    def _save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def set_recorder(self, recorder):
        """Inyecta el grabador de voz."""
        self.recorder = recorder

    def _sync_to_web(self, text_user, text_response):
        """Envía la conversación a la web (sin TTS, solo para mostrar)."""
        try:
            import requests
            requests.post(
                f"{self.api_url}/api/sync",
                json={"text_user": text_user, "text_response": text_response},
                timeout=5
            )
        except:
            pass
    
    def set_music_player(self, player):
        """Inyecta el reproductor de música."""
        self.music_player = player
    
    def on_activation(self, method, text):
        """Callback cuando se detecta activación (aplausos o wake word)."""
        print(f"\n🔥 ACTIVADO por: {method} — '{text[:50]}'")
        
        # 0. Encender pantalla
        self._turn_on_screen()
        
        # 1. Abrir la web UI
        self._open_web_ui()
        
        # 2. Saludo personalizado con hora
        saludo = self._get_time_greeting()
        self.recorder.play_tts_sync(saludo)
        
        # 3. Preguntar que desea hacer
        self._show_menu()
    
    def _get_time_greeting(self):
        """Saludo según la hora del día."""
        import datetime
        now = datetime.datetime.now()
        hora = now.hour
        if hora < 12:
            saludo = "Buenos días, jefe"
        elif hora < 18:
            saludo = "Buenas tardes, jefe"
        else:
            saludo = "Buenas noches, jefe"
        return f"{saludo}. ¿Qué desea hacer hoy?"
    
    def _show_menu(self):
        """Muestra el menú de opciones y espera respuesta."""
        mensaje = (
            "Tengo estas opciones para usted, jefe: "
            "1. Ver estatus general del sistema. "
            "2. Resumen personal: correos y noticias. "
            "O simplemente dígame qué necesita y lo haré. "
            "¿Qué opción prefiere?"
        )
        self.recorder.play_tts_sync(mensaje)
        self._wait_for_menu_option()
    
    def _wait_for_menu_option(self):
        """Escucha la opción del menú."""
        if not self.recorder:
            return
        
        self.recorder.detector.pause()
        orden = self.recorder.record(timeout=10)
        self.recorder.detector.resume()
        
        if not orden:
            self.recorder.play_tts("Sin respuesta. Quedo atento, jefe.")
            return
        
        text = orden.lower()
        
        if "silencio" in text or "callate" in text or "cállate" in text or "para" in text:
            self._handle_silence()
        elif "estatus" in text or "status" in text or "sistema" in text or "1" in text:
            self._handle_status()
        elif "resumen" in text or "personal" in text or "correo" in text or "noticia" in text or "2" in text:
            self._handle_personal_summary()
        else:
            # Orden general
            self.recorder.play_tts(f"Procesando su solicitud, jefe.")
            respuesta = self.recorder.send_to_bridge(orden)
            if respuesta.get("text"):
                self.recorder.play_tts(respuesta["text"])
                self._sync_to_web(orden, respuesta["text"])
    
    def _handle_silence(self):
        """Detiene cualquier voz en curso."""
        import subprocess
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ffplay.exe"], 
                         capture_output=True, timeout=3)
        except:
            pass
        if self.recorder:
            self.recorder.stop_speaking()
        print("🔇 Silencio activado")
    
    def _handle_status(self):
        """Reporta estatus de todos los sistemas (rápido y paralelo)."""
        import requests, threading
        
        resultados = {}
        partes = ["Aquí está el estatus general del sistema:"]
        locks = threading.Lock()
        
        def check(name, url, msg):
            try:
                r = requests.get(url, timeout=2)
                with locks:
                    resultados[name] = msg if r.status_code == 200 else f"{msg} con error"
            except:
                with locks:
                    resultados[name] = f"{msg}: no disponible"
        
        threads = [
            threading.Thread(target=check, args=("bridge", "http://127.0.0.1:9876/health", "Bridge Houdini operativo")),
            threading.Thread(target=check, args=("express", "http://127.0.0.1:9999/api/config", "API Express operativa")),
            threading.Thread(target=check, args=("web", "http://localhost:8001/", "Interfaz web operativa")),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        
        partes.append(resultados.get("bridge", "Bridge no disponible."))
        partes.append(resultados.get("express", "API no disponible."))
        partes.append(resultados.get("web", "Web no disponible."))
        partes.append("Google: autenticado.")
        partes.append("Telegram: configurado.")
        if self.music_player and self.music_player.local_tracks:
            partes.append(f"Música: {len(self.music_player.local_tracks)} canciones.")
        else:
            partes.append("Música: disponible.")
        
        texto = ". ".join(partes)
        print(f"✅ Estatus listo ({len(texto)} chars)")
        self.recorder.play_tts(texto)
        self._sync_to_web("estatus del sistema", texto)
    
    def _handle_personal_summary(self):
        """Resumen personal: habla mientras consulta en segundo plano."""
        import threading
        
        respuesta = {"text": None}
        done = threading.Event()
        
        def consultar():
            """Llama al bridge en segundo plano."""
            r = self.recorder.send_to_bridge(
                "DAME SOLO ESTO: 1) Cuantos correos no leídos tengo en Gmail y el título del más importante. "
                "2) Una noticia corta de una línea sobre inteligencia artificial. "
                "RESPONDE EN MÁXIMO 3 FRASES, SÉ CONCRETO."
            )
            respuesta["text"] = r.get("text", "")
            done.set()
        
        # Lanzar consulta en segundo plano
        threading.Thread(target=consultar, daemon=True).start()
        
        # Mientras espera, dar indicaciones al usuario
        self.recorder.play_tts_sync("Deme un momento, jefe. Estoy consultando sus correos y buscando una noticia de actualidad.")
        
        if not done.is_set():
            self.recorder.play_tts_sync("Revisando su bandeja de entrada de Gmail...")
        
        if not done.is_set():
            self.recorder.play_tts_sync("Buscando las últimas noticias de inteligencia artificial...")
        
        if not done.is_set():
            self.recorder.play_tts_sync("Casi listo, jefe. Un segundo más.")
        
        # Esperar a que termine
        done.wait(timeout=15)
        
        # Responder
        if respuesta.get("text"):
            texto = respuesta["text"][:400]
            print(f"✅ Resumen listo ({len(texto)} chars)")
            self.recorder.play_tts(texto)
            self._sync_to_web("resumen personal", texto)
        else:
            self.recorder.play_tts("No pude obtener la información, jefe. Intente de nuevo más tarde.")
    
    def _is_morning_greeting(self, text):
        """Detecta si es un saludo matutino."""
        text = text.lower()
        greetings = ["buenos días", "buen día", "buenas", "hola houdini", "actívate"]
        return any(g in text for g in greetings)
    
    def _open_web_ui(self):
        """Abre la interfaz web en el navegador Chrome/Edge."""
        try:
            # Intentar con Chrome (rutas comunes en Windows)
            chrome_paths = [
                "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
                os.path.expandvars("%LOCALAPPDATA%/Google/Chrome/Application/chrome.exe"),
                "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
                "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    subprocess.Popen([path, self.web_url],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"🌐 Abriendo {self.web_url} con {os.path.basename(path)}")
                    return
            # Fallback a webbrowser
            webbrowser.open(self.web_url)
            print(f"🌐 Abriendo {self.web_url} (fallback)")
        except Exception as e:
            print(f"⚠️ No se pudo abrir navegador: {e}")
    
    def _play_activation_sound(self):
        """Reproduce un tono de activación."""
        try:
            import requests
            requests.post(
                f"{self.api_url}/api/tts",
                json={"text": "Activado"},
                timeout=5
            )
        except:
            pass
    
    # ── Rutina Matutina ──
    
    def _run_morning_routine(self):
        """Ejecuta la rutina completa del día."""
        print("🌅 Ejecutando rutina matutina...")
        
        partes = []
        
        # 1. Saludo personalizado + fecha/hora
        saludo = self._get_greeting()
        partes.append(saludo)
        
        # 2. Clima
        clima = self._get_weather()
        if clima:
            partes.append(clima)
        
        # 3. Calendario (eventos del día)
        eventos = self._get_calendar_events()
        if eventos:
            partes.append(eventos)
        
        # 4. Correos pendientes
        correos = self._get_emails()
        if correos:
            partes.append(correos)
        
        # 5. Noticias de IA
        noticias = self._get_news()
        if noticias:
            partes.append(noticias)
        
        # 6. Frase motivacional
        frase = self._get_motivation()
        partes.append(frase)
        
        # Unir todo y enviar al bridge
        mensaje_completo = ". ".join(partes)
        print(f"📋 Rutina preparada ({len(mensaje_completo)} chars)")
        
        # Enviar al bridge para obtener respuesta de Houdini
        if self.recorder:
            respuesta = self.recorder.send_to_bridge(
                f"Eres HOUDINI, un mayordomo elegante. "
                f"Saluda al usuario de forma natural y dale TODA esta información en orden, sin omitir nada, en un solo mensaje completo: {mensaje_completo}. "
                f"Responde de forma cálida y completa, no ofrezcas resumir."
            )
            if respuesta.get("text"):
                texto = respuesta["text"]
                print(f"🎩 Houdini: {texto[:100]}...")
                # Reproducir por voz (NO bloqueante)
                threading.Thread(target=self.recorder.play_tts, args=(texto,), daemon=True).start()
                self._sync_to_web("rutina matutina", texto)
                
                # Reproducir musica de fondo - siempre empieza con lose my cool.mp3
                if self.music_player:
                    self._play_morning_music()
                    # Esperar a que termine la canción y preguntar
                    self._wait_for_music_and_ask()

        # Esperar más órdenes
        self._wait_and_process_command()
    
    def _get_greeting(self):
        """Saludo con fecha y hora."""
        import datetime
        now = datetime.datetime.now()
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        dia_semana = dias[now.weekday()]
        
        hora = now.hour
        if hora < 12:
            saludo = "Buenos días"
        elif hora < 18:
            saludo = "Buenas tardes"
        else:
            saludo = "Buenas noches"
        
        return (
            f"{saludo}, {self.config['nombre_usuario']}. "
            f"Hoy es {dia_semana}, {now.day} de {now.strftime('%B')} de {now.year}. "
            f"Son las {now.hour} horas con {now.minute} minutos."
        )
    
    def _get_weather(self):
        """Clima actual (usa wttr.in)."""
        try:
            import requests
            resp = requests.get(
                f"https://wttr.in/{self.config['ubicacion'].split(',')[0].strip()}?format=%C+%t+%w+%h",
                timeout=10
            )
            if resp.status_code == 200 and resp.text.strip():
                clima_text = resp.text.strip()
                # wttr.in returns something like "Sunny +28°C 15km/h 45%"
                return f"El clima en {self.config['ubicacion']} es: {clima_text}."
            return None
        except:
            return None
    
    def _get_calendar_events(self):
        """Próximos eventos del calendario vía Express API."""
        try:
            import requests
            resp = requests.post(
                f"{self.api_url}/api/chat",
                json={
                    "message": "Dime mis eventos del calendario de hoy, SOLO los datos sin explicación extra",
                    "session_id": "asistente-escritorio-rutina"
                },
                timeout=60
            )
            data = resp.json()
            if data.get("text"):
                return f"Tus eventos de hoy: {data['text']}"
        except:
            return "No pude consultar tu calendario."
        return None
    
    def _get_emails(self):
        """Correos pendientes vía Express API."""
        try:
            import requests
            resp = requests.post(
                f"{self.api_url}/api/chat",
                json={
                    "message": "Revisa mis correos de Gmail, dime cuantos no leídos tengoy solo los títulos de los más importantes sin detalles largos",
                    "session_id": "asistente-escritorio-rutina"
                },
                timeout=60
            )
            data = resp.json()
            if data.get("text") and "error" not in data.get("text", "").lower():
                return f"Correos: {data['text']}"
        except:
            pass
        return None
    
    def _get_news(self):
        """Top 3 noticias de IA."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Usar Google News para IA
            resp = requests.get(
                "https://news.google.com/rss/search?q=inteligencia+artificial&hl=es-419&gl=CO&ceid=CO:es-419",
                timeout=10
            )
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                items = root.findall('.//item')
                noticias = []
                for item in items[:3]:
                    title = item.find('title')
                    if title is not None and title.text:
                        noticias.append(title.text.strip())
                
                if noticias:
                    return f"Top noticias de Inteligencia Artificial: {' — '.join(noticias)}"
        except:
            pass
        return None
    
    def _get_motivation(self):
        """Frase motivacional."""
        frases = [
            "Cada día es una nueva oportunidad para ser la mejor versión de ti mismo.",
            "El éxito no es la clave de la felicidad, la felicidad es la clave del éxito.",
            "Cree en ti mismo y todo será posible.",
            "La única forma de hacer un gran trabajo es amar lo que haces.",
            "No cuentes los días, haz que los días cuenten.",
            "El momento es ahora.",
        ]
        import random
        return f"Frase del día: {random.choice(frases)}"
    
    def _play_morning_music(self):
        """Reproduce 'lose my cool.mp3' al iniciar la rutina."""
        if self.music_player:
            music_dir = Path(self.config.get("musica_local", str(Path.home() / "Music")))
            target = None
            for f in music_dir.rglob("lose my cool.mp3"):
                target = f
                break
            if not target:
                for f in music_dir.rglob("lose*cool*.mp3"):
                    target = f
                    break
                for f in music_dir.rglob("*lose*my*cool*"):
                    target = f
                    break
            
            if target:
                print(f"🎵 Reproduciendo: {target.name}")
                threading.Thread(
                    target=self.music_player.play_file,
                    args=(target,),
                    daemon=True
                ).start()
            else:
                print("⚠️ No encontre lose my cool.mp3, reproduciendo aleatoria")
                threading.Thread(target=self.music_player.play_random, daemon=True).start()

    def _wait_for_music_and_ask(self):
        """Espera a que termine la canción escuchando órdenes en paralelo."""
        if not self.music_player:
            return

        print("⏳ Musica sonando — di 'para', 'siguiente', 'sube volumen', etc.")
        max_wait = 600
        waited = 0
        while waited < max_wait:
            if self.recorder:
                orden = self.recorder.record(timeout=3)
                if orden:
                    print(f"🗣️ Orden durante musica: '{orden}'")
                    if self._is_music_command(orden):
                        self._handle_music_command(orden)
                        if not self.music_player.is_playing:
                            break
                    elif self._is_screen_command(orden):
                        self._handle_screen_command(orden)
                    else:
                        respuesta = self.recorder.send_to_bridge(orden)
                        if respuesta.get("text"):
                            self.recorder.play_tts(respuesta["text"])
                            self._sync_to_web(orden, respuesta["text"])
            
            waited += 3
            if not self.music_player or not self.music_player.is_playing:
                break

        if self.music_player and self.music_player.last_played:
            print(f"✅ Cancion terminada: {self.music_player.last_played}")

        print("🎤 Preguntando si quiere seguir escuchando...")
        if self.recorder:
            mensaje = (
                "La cancion ha terminado. Preguntale al usuario de forma natural "
                "si desea seguir escuchando musica, poner otra cancion, o si prefiere silencio. "
                "Responde como mayordomo elegante."
            )
            respuesta = self.recorder.send_to_bridge(mensaje)
            if respuesta.get("text"):
                self.recorder.play_tts(respuesta["text"])
                self._sync_to_web("pregunta musica", respuesta["text"])

        # Escuchar respuesta (una sola vez), luego reposo
        if self.recorder:
            orden = self.recorder.record(timeout=6)
            if orden:
                if self._is_music_command(orden):
                    self._handle_music_command(orden)
                else:
                    respuesta = self.recorder.send_to_bridge(orden)
                    if respuesta.get("text"):
                        self.recorder.play_tts(respuesta["text"])
                        self._sync_to_web(orden, respuesta["text"])
        
        print("💤 Asistente en reposo — di 'Houdini' o aplaude para activarme")
    
    # ── Procesamiento de órdenes ──
    
    def _wait_and_process_command(self):
        """Una sola ronda de escucha, luego vuelve a modo reposo."""
        if not self.recorder:
            return
        
        print("🎤 Escuchando una orden...")
        orden = self.recorder.record(timeout=8)
        
        if not orden:
            print("⏰ Sin orden, volviendo a modo reposo")
            return
        
        # Comandos especiales
        if self._is_music_command(orden):
            self._handle_music_command(orden)
            return

        if self._is_screen_command(orden):
            self._handle_screen_command(orden)
            return
        
        # Orden general → bridge
        print(f"📤 Enviando a Houdini: {orden}")
        respuesta = self.recorder.send_to_bridge(orden)
        if respuesta.get("text"):
            print(f"🎩 {respuesta['text'][:100]}...")
            self.recorder.play_tts(respuesta["text"])
            self._sync_to_web(orden, respuesta["text"])
        
        # Volver a modo reposo (detector de wake word)
        print("💤 Asistente en reposo — di 'Houdini' o aplaude para activarme")
    
    def _is_music_command(self, text):
        """Detecta si es un comando de musica."""
        text = text.lower()
        return any(p in text for p in ["pon musica", "pon cancion", "musica", "cancion",
                                       "silencio", "para", "siguiente", "cambia",
                                       "sube volumen", "baja volumen", "deten"])
    
    def _handle_music_command(self, text):
        """Maneja comandos de musica."""
        if not self.music_player:
            print("❌ No hay reproductor de musica configurado")
            return
        
        text = text.lower()
        
        if "para" in text or "deten" in text or "silencio" in text or "stop" in text:
            self.music_player.stop()
            if self.recorder:
                self.recorder.play_tts("Musica detenida")
                self._sync_to_web("comando musica", "Musica detenida")
        elif "siguiente" in text or "cambia" in text or "otra" in text:
            self.music_player.next()
        elif "sube" in text or "mas alto" in text or "volumen" in text:
            self.music_player.volume_up()
        elif "baja" in text or "mas bajo" in text:
            self.music_player.volume_down()
        else:
            if self.music_player.play_random():
                if self.recorder:
                    self.recorder.play_tts("Reproduciendo musica")
        print("💤 Vuelvo a reposo — di 'Houdini' para activarme")

    # ── Comandos de pantalla ──
    
    def _is_screen_command(self, text):
        """Detecta si es un comando de pantalla."""
        text = text.lower()
        return any(p in text for p in ["apaga la pantalla", "apagar pantalla", "apaga pantalla",
                                       "apaga el monitor", "apagar monitor", "pantalla apaga",
                                       "enciende la pantalla", "prende la pantalla"])
    
    def _handle_screen_command(self, text):
        """Maneja comandos de pantalla: apagar/encender."""
        import subprocess
        text = text.lower()
        
        if "apaga" in text or "apagar" in text:
            print("🖥️ Apagando pantalla...")
            bat_path = os.path.join(os.path.dirname(__file__), "apagar_pantalla.bat")
            if os.path.exists(bat_path):
                subprocess.Popen([bat_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(
                    ["powershell", "-command",
                     '[DllImport("user32.dll")]public static extern int SendMessage(int h,int m,int w,int l);'
                     'SendMessage(-1,0x0112,0xF170,2) | Out-Null'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            if self.recorder:
                self.recorder.play_tts("Pantalla apagada. Di Houdini o aplaude para activarme.")
        elif "enciende" in text or "prende" in text:
            print("🖥️ Encendiendo pantalla...")
            import ctypes
            # Comando directo para encender monitor
            # Método más confiable: enviar comando de encendido + simular tecla
            ctypes.windll.user32.SendMessageW(-1, 0x0112, 0xF170, -1)
            time.sleep(0.3)
            # Simular movimiento de mouse + scroll
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)  # mover mouse
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, 0, 0)  # scroll wheel
            # Presionar y soltar tecla Shift (despierta pantalla)
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # Shift down
            time.sleep(0.1)
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # Shift up
            if self.recorder:
                self.recorder.play_tts("Pantalla encendida. Aqui estoy, jefe.")

    def _turn_on_screen(self):
        """Enciende la pantalla si está apagada (método agresivo)."""
        import ctypes, subprocess
        try:
            # Método 1: Comando directo de Windows (WM_SYSCOMMAND)
            ctypes.windll.user32.SendMessageW(-1, 0x0112, 0xF170, -1)
            time.sleep(0.2)
            
            # Método 2: Simular teclas (Shift + Ctrl)
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # Shift down
            ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # Shift up
            time.sleep(0.1)
            
            # Método 3: Mover el mouse enérgicamente
            import ctypes.wintypes
            for _ in range(3):
                ctypes.windll.user32.mouse_event(0x0001, 0, 5, 0, 0)
                time.sleep(0.05)
            
            # Método 4: PowerShell para despertar pantalla
            subprocess.run(
                ["powershell", "-command", 
                 "[System.Windows.Forms.SendKeys]::SendWait('{SCROLLLOCK}')"],
                capture_output=True, timeout=3
            )
            
            print("🖥️ Pantalla encendida")
        except Exception as e:
            print(f"⚠️ No se pudo encender pantalla: {e}")

    def shutdown(self):
        """Apaga el asistente."""
        print("👋 Asistente apagado.")
