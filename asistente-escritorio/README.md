# 🎩 Houdini Desktop — Asistente Always-On

Asistente de escritorio tipo Jarvis/Alexa que escucha 24/7, se activa con 👏 **aplausos** o diciendo **"Houdini"**, y ejecuta tu rutina matutina completa por voz.

## 🏗️ Arquitectura

```
🎤 MICRÓFONO (PC)
    ↓
┌──────────────────────────────────┐
│  Asistente Desktop (Python)      │
│  • Detecta aplausos (numpy)      │
│  • Wake word (speech_recognition)│
│  • Graba órdenes por voz         │
│  • Reproduce TTS (Salome)        │
└──────────────┬───────────────────┘
               ↓ texto
┌──────────────────────────────────┐
│  Houdini Bridge (Python :9876)  │
│  • Claude Sonnet 4.5            │
│  • Tool calls (Gmail, Calendar, │
│    Telegram, Sheets, Drive)     │
└──────────────┬───────────────────┘
         ┌─────┴─────┐
         ↓           ↓
    🖥️ Web UI    🔊 Voz Salome
     (:8001)     (edge-tts)
```

## 🚀 Cómo usar

### 1. Arrancar los servicios

```bash
cd server
python houdini-bridge.py     # Bridge Houdini
cd ..
node server/index.js         # API Express
```

O usa el launcher:
```bash
cd asistente-escritorio
./launcher.sh
```

### 2. Abrir la web
```
http://localhost:8001/
```

### 3. Iniciar el asistente de escritorio
```bash
cd asistente-escritorio
source .venv/Scripts/activate
python main.py
```

## 🎯 Activación

| Método | Cómo |
|---|---|
| 👏 **Aplausos** | Aplaude **2 veces** seguidas (máx 0.8s entre ellos) |
| 🗣️ **Wake word** | Di "Houdini", "Actívate" o "Hola Houdini" |

## 🌅 Rutina Matutina

Al activarte con un saludo o aplausos, Houdini ejecuta:

1. ✅ **Saludo personalizado** con fecha, hora y día de la semana
2. 🌤️ **Clima en Medellín** (vía wttr.in)
3. 📅 **Tus eventos del calendario de hoy**
4. 📧 **Correos pendientes de Gmail**
5. 📰 **Top 3 noticias de Inteligencia Artificial**
6. 💪 **Frase motivacional del día**
7. 🎵 **Reproduce música de fondo**

## 🎵 Control de Música

| Comando de voz | Acción |
|---|---|
| "Pon música / Pon una canción" | Reproduce música aleatoria |
| "Para / Silencio / Detén" | Detiene la música |
| "Siguiente / Cambia" | Siguiente canción |
| "Sube volumen" / "Baja volumen" | Control de volumen |

### Música Local
Las canciones se buscan en tu carpeta `~/Music/` (configurable).

### Spotify
Para activar Spotify, edita `config.json`:
```json
"spotify": {
    "enabled": true,
    "client_id": "TU_CLIENT_ID",
    "client_secret": "TU_CLIENT_SECRET"
}
```
Crea una app en https://developer.spotify.com/dashboard

## 🔧 Requisitos

- Python 3.11+
- Node.js 20+
- ffmpeg (para reproducción de audio)
- Micrófono funcionando

## 📁 Estructura del proyecto

```
proyecto hermes/
├── asistente-escritorio/     ← NUEVO
│   ├── main.py               # Punto de entrada
│   ├── detector.py           # Clap + wake word detection
│   ├── assistant.py          # Rutina matutina + órdenes
│   ├── music.py              # Reproductor local + Spotify
│   ├── config.json           # Configuración
│   ├── launcher.sh           # Arranca todo
│   └── .venv/                # Virtual environment
├── openclaw-jarvis-ui/       # Web UI 3D
│   ├── server/               # Express API + Bridge
│   └── src/                  # Frontend React
└── houdini/                  # Core de Houdini
```

## 📝 Configuración

Edita `config.json`:
```json
{
  "nombre_usuario": "Jefe",
  "ubicacion": "Medellín, Colombia",
  "musica_local": "C:\\Users\\USER\\Music",
  "spotify": { "enabled": false }
}
```