"""
Houdini - TelegramAgent
Sub-agente para Telegram: enviar mensajes, notificaciones, polling, recordatorios.
"""
import asyncio
import re
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message as TgMessage, CallbackQuery
from aiogram.filters import Command
from schemas.tools import SendMessageInput, ScheduleReminderInput
from core.memory import MemoryStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

logger = logging.getLogger("houdini.agents.telegram")


def clean_markdown(text: str) -> str:
    """Elimina todo formato Markdown: asteriscos, numerales, underscores, etc."""
    # Eliminar **texto** (negrita)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Eliminar *texto* (cursiva)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Eliminar _texto_ (cursiva/underscore)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Eliminar __texto__ (negrita con underscore)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Eliminar `texto` (código)
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Eliminar al inicio de línea: ###, ##, #
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Eliminar - o * al inicio de línea (listas no ordenadas)
    text = re.sub(r'^[\s]*[-*+]\s+', '  ', text, flags=re.MULTILINE)
    # Eliminar > (blockquote)
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    # Eliminar saludos de hora: "buenos días", "buenas tardes", "buenas noches"
    text = re.sub(r'(?i)\bbuenos?\s+d[ií]as?\b', '', text)
    text = re.sub(r'(?i)\bbuenas?\s+(noches|tardes)\b', '', text)
    # Limpiar espacios dobles y comas sobrantes después de eliminar saludos
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r'🎩\s*,', '🎩', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


class TelegramAgent:
    """Sub-agente para Telegram con polling, comandos y recordatorios."""

    def __init__(self, bot_token: str, memory: MemoryStore):
        self.bot = Bot(token=bot_token)
        self.dp = Dispatcher()
        self.memory = memory
        self.chat_id: Optional[str] = None
        self._orchestrator_callback: Optional[Callable] = None

        # Scheduler para recordatorios (persistente en PostgreSQL)
        scheduler_store = SQLAlchemyJobStore(
            url=memory.engine.url.render_as_string(hide_password=False)
        )
        self.scheduler = AsyncIOScheduler(jobstores={"default": scheduler_store})

        self._register_handlers()

    def _register_handlers(self):
        """Registra los command handlers."""

        @self.dp.message(Command("start"))
        async def cmd_start(message: TgMessage):
            self.chat_id = str(message.chat.id)
            await message.answer(
                "🎩 *Houdini inicializado*\n\n"
                "Soy tu asistente personal. Puedes:\n"
                "• Escribirme directamente cualquier tarea\n"
                "• /recordar <tiempo> <mensaje> — programar recordatorio\n"
                "• /tareas — ver tareas pendientes\n"
                "• /estado — salud del sistema\n"
                "• /ayuda — ver esta ayuda",
                parse_mode="Markdown",
            )

        @self.dp.message(Command("ayuda"))
        async def cmd_ayuda(message: TgMessage):
            await message.answer(
                "🎩 *Comandos de Houdini*\n\n"
                "/start — Iniciar\n"
                "/recordar 30m revisar correo — Recordatorio en 30 min\n"
                "/recordar 14:00 reunión — Recordatorio a las 2 PM\n"
                "/tareas — Tareas pendientes\n"
                "/estado — Estado del sistema\n"
                "Cualquier texto → lo proceso como tarea",
                parse_mode="Markdown",
            )

        @self.dp.message(Command("recordar"))
        async def cmd_recordar(message: TgMessage):
            """Programa un recordatorio. Formatos:
            /recordar 30m revisar correo
            /recordar 2h llamar a Carlos
            /recordar 14:00 reunión con equipo
            """
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                await message.answer("❌ Uso: /recordar <tiempo> <mensaje>\nEj: /recordar 30m revisar correo")
                return

            parts = args[1].split(maxsplit=1)
            time_str = parts[0]
            msg_text = parts[1] if len(parts) > 1 else "Recordatorio"

            run_at = self._parse_time(time_str)
            if run_at is None:
                await message.answer(f"❌ Formato de tiempo no válido: {time_str}\nUsa: 30m, 2h, 14:00, mañana")
                return

            chat_id = str(message.chat.id)
            reminder = self.memory.create_reminder(chat_id, msg_text, run_at)

            # Programar job en APScheduler
            self.scheduler.add_job(
                self._send_reminder,
                "date",
                run_date=run_at,
                args=[chat_id, msg_text, str(reminder.id)],
                id=f"reminder_{reminder.id}",
            )

            await message.answer(
                f"✅ Recordatorio programado para {run_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"📋 Mensaje: {msg_text}"
            )

        @self.dp.message(Command("tareas"))
        async def cmd_tareas(message: TgMessage):
            tasks = self.memory.get_pending_tasks()
            if not tasks:
                await message.answer("✅ No hay tareas pendientes")
                return
            lines = ["📋 *Tareas pendientes:*\n"]
            for t in tasks:
                lines.append(f"• [{t['status']}] {t['type']} (paso {t['step']})")
            await message.answer("\n".join(lines), parse_mode="Markdown")

        @self.dp.message(Command("estado"))
        async def cmd_estado(message: TgMessage):
            await message.answer(
                "🟢 *Houdini - Estado del sistema*\n\n"
                f"• Bot: ✅ Activo\n"
                f"• Scheduler: {'✅' if self.scheduler.running else '❌'}\n"
                f"• Memoria: ✅ Conectada\n"
                f"• Modelo: Nemotron 3 Ultra → GPT-4o fallback",
                parse_mode="Markdown",
            )

        @self.dp.message(F.text)
        async def handle_free_text(message: TgMessage):
            """Texto libre → pasa al orquestador Houdini."""
            if message.text.startswith("/"):
                return
            self.chat_id = str(message.chat.id)
            chat_id = message.chat.id

            if self._orchestrator_callback:
                try:
                    response = await self._orchestrator_callback(
                        message.text, str(chat_id)
                    )
                    # Limpiar markdown antes de enviar
                    cleaned = clean_markdown(response or "Hecho")
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=cleaned
                    )
                except Exception as e:
                    logger.error(f"Error orquestador: {e}", exc_info=True)
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=clean_markdown(f"Error: {e}")
                    )
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Orquestador no conectado"
                )

    def set_orchestrator_callback(self, callback):
        """Inyecta la función que procesa texto libre via Houdini."""
        self._orchestrator_callback = callback

    async def send_message(self, params: SendMessageInput) -> dict:
        """Envía un mensaje por Telegram (limpio de markdown)."""
        try:
            await self.bot.send_message(
                chat_id=params.chat_id,
                text=clean_markdown(params.text),
                parse_mode=params.parse_mode,
            )
            return {"status": "sent", "chat_id": params.chat_id}
        except Exception as e:
            return {"error": str(e)}

    async def schedule_reminder(self, params: ScheduleReminderInput) -> dict:
        """Programa un recordatorio via tool call."""
        run_at = datetime.fromisoformat(params.run_at)
        reminder = self.memory.create_reminder(
            params.chat_id, params.text, run_at
        )
        self.scheduler.add_job(
            self._send_reminder,
            "date",
            run_date=run_at,
            args=[params.chat_id, params.text, str(reminder.id)],
            id=f"reminder_{reminder.id}",
        )
        return {"reminder_id": str(reminder.id), "run_at": params.run_at}

    async def _send_reminder(self, chat_id: str, text: str, reminder_id: str):
        """Callback del scheduler: envía el recordatorio."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ *Recordatorio*\n\n{text}",
                parse_mode="Markdown",
            )
            self.memory.mark_reminder_sent(reminder_id)
            logger.info(f"Recordatorio enviado: {reminder_id}")
        except Exception as e:
            logger.error(f"Error enviando recordatorio {reminder_id}: {e}")

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parsea diferentes formatos de tiempo."""
        now = datetime.now()
        time_str = time_str.lower().strip()

        # Formato: 30m, 2h
        if time_str.endswith("m") and time_str[:-1].isdigit():
            minutes = int(time_str[:-1])
            return now.replace(second=0) + timedelta(minutes=minutes)
        if time_str.endswith("h") and time_str[:-1].isdigit():
            hours = int(time_str[:-1])
            return now.replace(second=0) + timedelta(hours=hours)

        # Formato: 14:00
        if ":" in time_str:
            try:
                hour, minute = map(int, time_str.split(":"))
                target = now.replace(hour=hour, minute=minute, second=0)
                if target < now:
                    target += timedelta(days=1)
                return target
            except ValueError:
                pass

        # Formato: mañana
        if time_str == "mañana":
            return now.replace(hour=9, minute=0, second=0) + timedelta(days=1)

        return None

    async def start(self):
        """Inicia el bot en modo polling + scheduler (con reconexión automática)."""
        self.scheduler.start()
        logger.info("Telegram scheduler iniciado")
        while True:
            try:
                await self.dp.start_polling(self.bot)
            except Exception as e:
                logger.error(f"Telegram polling error: {e}. Reconectando en 5s...")
            await asyncio.sleep(5)

    async def stop(self):
        """Detiene bot y scheduler."""
        self.scheduler.shutdown(wait=False)
        await self.dp.stop_polling()
        await self.bot.session.close()
