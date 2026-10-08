# 🎩 Houdini

Agente personal orquestador con sub-agentes especializados, memoria persistente y múltiples canales de interacción.

## 📦 Estructura del Proyecto

```
houdini/
├── main.py                    # Punto de entrada
├── requirements.txt           # Dependencias Python
├── docker-compose.yml         # PostgreSQL + pgvector
├── .env.example               # Template de variables de entorno
├── .env                       # Tus claves (no se commitea)
│
├── config/                    # Configuración
│   ├── settings.py            # Settings tipados (Pydantic)
│   ├── google_client_secret.json  # OAuth de Google (tú lo descargas)
│   └── google_token.json      # Token OAuth (auto-generado)
│
├── core/                      # Núcleo del sistema
│   ├── orchestrator.py        # Houdini orquestador (LLM + function calling)
│   ├── dispatcher.py          # Dispatcher de tools a sub-agentes
│   └── memory.py              # Memoria persistente (5 tipos)
│
├── agents/                    # Sub-agentes especializados
│   ├── gmail_agent.py         # Gmail: enviar, buscar, leer
│   ├── calendar_agent.py      # Google Calendar: crear, listar, actualizar
│   ├── sheets_agent.py        # Google Sheets: leer, escribir
│   ├── drive_agent.py         # Google Drive: subir, buscar, descargar
│   ├── telegram_agent.py      # Telegram: bot, comandos, recordatorios
│   ├── tts_agent.py           # Voz Salome (edge-tts)
│   └── whatsapp_agent.py      # WhatsApp (fase 2)
│
├── schemas/                   # Contratos de tools (Pydantic)
│   └── tools.py               # Definición de todas las tools
│
├── services/                  # Servicios compartidos
│   └── oauth.py               # Google OAuth2
│
├── models/                    # Modelos de base de datos
│   └── database.py            # 6 tablas (SQLAlchemy + pgvector)
│
└── scripts/                   # Scripts utilitarios
    ├── setup.sh               # Setup inicial
    ├── start.sh               # Iniciar
    └── stop.sh                # Detener
```

## 🚀 Instalación Rápida

### 1. Configurar entorno
```bash
cd houdini
cp .env.example .env
# Edita .env con tus claves
```

### 2. Setup inicial
```bash
bash scripts/setup.sh
```

### 3. Crear bot de Telegram
1. Abre Telegram y busca `@BotFather`
2. Envía `/newbot`
3. Sigue las instrucciones (nombre + username)
4. Copia el token a `.env`: `TELEGRAM_BOT_TOKEN=tu_token`

### 4. Configurar Google OAuth
1. Ve a [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Crea un proyecto → habilita APIs: Gmail, Calendar, Sheets, Drive
3. Crea credenciales OAuth 2.0 (tipo: Desktop app)
4. Descarga el JSON y guárdalo como `config/google_client_secret.json`

### 5. Iniciar
```bash
bash scripts/start.sh
# o directamente:
python main.py
```

## 🎯 Arquitectura

```
Usuario (Telegram/CLI/Voz)
    │
    ▼
┌─────────────────────────┐
│   Houdini (Orquestador)  │  ← Nemotron 3 Ultra → GPT-4o fallback
│   - Function calling     │
│   - Plan-then-execute    │
└──────────┬──────────────┘
           │
    ┌──────┴──────┐
    │  Dispatcher  │
    └──────┬──────┘
           │
    ┌──────┴──────────────────────────┐
    │            │         │         │
  Gmail    Calendar   Sheets    Drive   Telegram   TTS
    │            │         │         │         │        │
    └────────────┴─────────┴─────────┘         │
                                               │
                                    ┌──────────┴──────────┐
                                    │  PostgreSQL +        │
                                    │  pgvector (memoria)  │
                                    │  - Episódica         │
                                    │  - Semántica         │
                                    │  - Procedimental     │
                                    │  - Tareas            │
                                    │  - Documentos (RAG)  │
                                    │  - Recordatorios     │
                                    └─────────────────────┘
```

## 📋 Comandos de Telegram

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/start` | Iniciar bot | - |
| `/ayuda` | Ver ayuda | - |
| `/recordar <tiempo> <msg>` | Programar recordatorio | `/recordar 30m revisar correo` |
| `/recordar 14:00 reunión` | Recordar a hora específica | - |
| `/tareas` | Ver tareas pendientes | - |
| `/estado` | Salud del sistema | - |
| Texto libre | → Houdini procesa | "envía correo a Carlos" |

## 🔧 Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.11+ |
| LLM | OpenRouter (GPT-4o → DeepSeek V3 fallback) |
| DB | PostgreSQL 16 + pgvector |
| Memoria | SQLAlchemy async + pgvector embeddings |
| Telegram | aiogram 3.x |
| Scheduler | APScheduler (PostgreSQL jobstore) |
| TTS | edge-tts (voz Salome es-CO-SalomeNeural) |
| Google | google-api-python-client + OAuth2 |
| Infra | Docker Compose (local → VPS) |

## 🔄 Pendientes (Fase 2)

- [ ] WhatsApp (enviar mensajes)
- [ ] Integración handy.computer (Ctrl + <>)
- [ ] Comandos de voz (STT → Houdini → TTS)
- [ ] Migración a VPS (webhook en vez de polling)
- [ ] RAG avanzado (chunk-level embeddings)
- [ ] Panel web de administración
