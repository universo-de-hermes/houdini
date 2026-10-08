"""
Houdini - Punto de entrada principal
Inicia el orquestador, sub-agentes, memoria y Telegram bot.
"""
import asyncio
import logging
import sys

from config.settings import get_settings
from core.orchestrator import HoudiniOrchestrator
from core.dispatcher import ToolDispatcher
from core.memory import MemoryStore
from schemas.tools import ToolCategory, SpeakInput
from services.oauth import GoogleOAuth
from agents.gmail_agent import GmailAgent
from agents.calendar_agent import CalendarAgent
from agents.sheets_agent import SheetsAgent
from agents.drive_agent import DriveAgent
from agents.telegram_agent import TelegramAgent
from agents.tts_agent import TTSAgent
from agents.whatsapp_agent import WhatsAppAgent
from agents.design_agent import DesignAgent
from agents.dashboard_agent import DashboardAgent

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("houdini.main")
settings = get_settings()


async def main():
    """Punto de entrada principal de Houdini."""
    logger.info("🎩 Iniciando Houdini...")

    # 1. ── Inicializar memoria (PostgreSQL + pgvector) ──
    memory = MemoryStore()
    memory.init_db()
    logger.info("✅ Memoria inicializada (PostgreSQL + pgvector)")

    # 2. ── Inicializar sub-agentes ──
    dispatcher = ToolDispatcher()

    # TTS (siempre disponible, no requiere OAuth)
    tts = TTSAgent(
        voice=settings.tts_voice,
        rate=settings.tts_rate,
        volume=settings.tts_volume,
    )
    dispatcher.register_agent(ToolCategory.TTS, tts)

    # Google OAuth (Gmail, Calendar, Sheets, Drive)
    oauth = GoogleOAuth()
    google_creds = oauth.get_credentials()

    if google_creds:
        gmail = GmailAgent(credentials=google_creds)
        calendar = CalendarAgent(credentials=google_creds)
        sheets = SheetsAgent(credentials=google_creds)
        drive = DriveAgent(credentials=google_creds)
        logger.info("✅ Google services autenticados (Gmail, Calendar, Sheets, Drive)")
    else:
        gmail = GmailAgent()
        calendar = CalendarAgent()
        sheets = SheetsAgent()
        drive = DriveAgent()
        logger.warning("⚠️ Google no autenticado. Ejecuta setup de OAuth primero.")

    dispatcher.register_agent(ToolCategory.GMAIL, gmail)
    dispatcher.register_agent(ToolCategory.CALENDAR, calendar)
    dispatcher.register_agent(ToolCategory.SHEETS, sheets)
    dispatcher.register_agent(ToolCategory.DRIVE, drive)

    # WhatsApp (fase 2)
    whatsapp = WhatsAppAgent(enabled=settings.whatsapp_enabled)
    dispatcher.register_agent(ToolCategory.WHATSAPP, whatsapp)

    # Design (HTML templates)
    design = DesignAgent()
    dispatcher.register_agent(ToolCategory.DESIGN, design)
    logger.info("✅ Design Agent (HTML Bootstrap) registrado")

    # Dashboard (reportes Membresías VIP)
    dashboard = DashboardAgent()
    dispatcher.register_agent(ToolCategory.DASHBOARD, dashboard)
    logger.info("✅ Dashboard Agent (Membresias VIP) registrado")

    # 3. ── Inicializar orquestador ──
    orchestrator = HoudiniOrchestrator()
    orchestrator.set_tool_executor(dispatcher)
    logger.info("✅ Orquestador inicializado")

    # 4. ── Inicializar Telegram (si hay token) ──
    if settings.telegram_bot_token:
        telegram = TelegramAgent(
            bot_token=settings.telegram_bot_token,
            memory=memory,
        )

        # Callback: texto libre de Telegram → Houdini orquestador
        async def handle_telegram_text(text: str, chat_id: str) -> str:
            # Obtener contexto (memoria episódica)
            history = memory.get_history(chat_id, limit=10)

            # Ejecutar orquestador
            response = await orchestrator.orchestrate(
                user_text=text,
                session_id=chat_id,
                context=history,
            )

            # Guardar conversación en memoria
            memory.save_conversation(chat_id, "user", text)
            memory.save_conversation(chat_id, "assistant", response.text)

            # TTS: si está habilitado, generar audio
            if settings.tts_enabled and response.text:
                await tts.speak(SpeakInput(text=response.text))

            return response.text

        telegram.set_orchestrator_callback(handle_telegram_text)
        dispatcher.register_agent(ToolCategory.TELEGRAM, telegram)
        logger.info("✅ Telegram bot inicializado")

        # Iniciar polling + scheduler
        logger.info("🎩 Houdini listo. Esperando mensajes en Telegram...")
        await telegram.start()
    else:
        logger.warning("⚠️ Sin TELEGRAM_BOT_TOKEN. Modo CLI.")
        await run_cli(orchestrator, memory, tts)

    # Cleanup
    memory.close()


async def run_cli(orchestrator: HoudiniOrchestrator, memory: MemoryStore, tts: TTSAgent):
    """Modo CLI interactivo (sin Telegram)."""
    logger.info("Modo CLI. Escribe 'salir' para terminar.")
    session_id = "cli_session"

    while True:
        try:
            user_input = input("\n👤 Tú: ").strip()
            if user_input.lower() in ["salir", "exit", "quit"]:
                break
            if not user_input:
                continue

            # Obtener contexto
            history = memory.get_history(session_id, limit=10)

            # Orquestar
            response = await orchestrator.orchestrate(
                user_text=user_input,
                session_id=session_id,
                context=history,
            )

            # Guardar en memoria
            memory.save_conversation(session_id, "user", user_input)
            memory.save_conversation(session_id, "assistant", response.text)

            print(f"\n🎩 Houdini: {response.text}")

            # TTS
            if settings.tts_enabled and response.text:
                await tts.speak(SpeakInput(text=response.text))

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
