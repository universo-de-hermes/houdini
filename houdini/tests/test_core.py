"""
Houdini - Tests básicos
Tests de schemas y dispatcher (sin requerir DB ni APIs externas).
"""
import pytest
from schemas.tools import (
    TOOL_REGISTRY, SendEmailInput, ScheduleReminderInput, SpeakInput, ToolCategory
)


class TestSchemas:
    def test_send_email_input(self):
        inp = SendEmailInput(to="test@example.com", subject="Test", body="Hola")
        assert inp.to == "test@example.com"
        assert inp.attachments == []

    def test_schedule_reminder_input(self):
        inp = ScheduleReminderInput(
            chat_id="123", text="Recordar", run_at="2025-01-15T14:00:00"
        )
        assert inp.chat_id == "123"

    def test_speak_input_defaults(self):
        inp = SpeakInput(text="Hola mundo")
        assert inp.voice == "es-CO-SalomeNeural"

    def test_tool_registry_has_all_tools(self):
        expected_tools = [
            "send_email", "search_emails", "read_email",
            "create_event", "list_events", "update_event", "find_free_slots",
            "read_range", "write_range",
            "upload_file", "search_files", "download_file",
            "send_message", "schedule_reminder",
            "speak",
        ]
        for tool in expected_tools:
            assert tool in TOOL_REGISTRY, f"Tool faltante: {tool}"

    def test_tool_registry_categories(self):
        assert TOOL_REGISTRY["send_email"]["category"] == ToolCategory.GMAIL
        assert TOOL_REGISTRY["create_event"]["category"] == ToolCategory.CALENDAR
        assert TOOL_REGISTRY["speak"]["category"] == ToolCategory.TTS


class TestDispatcher:
    def test_dispatch_unknown_tool(self):
        from core.dispatcher import ToolDispatcher
        d = ToolDispatcher()
        import asyncio
        result = asyncio.run(d.dispatch("nonexistent_tool", {}))
        assert "error" in result

    def test_dispatch_invalid_args(self):
        from core.dispatcher import ToolDispatcher
        d = ToolDispatcher()
        import asyncio
        result = asyncio.run(d.dispatch("send_email", {"to": "no-email"}))
        assert "error" in result
