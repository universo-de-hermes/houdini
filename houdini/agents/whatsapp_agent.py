"""
Houdini - WhatsAppAgent (fase 2)
Sub-agente para WhatsApp via WhatsApp Business API / Baileys.
Placeholder - se implementará cuando Telegram esté funcionando.
"""
import logging
from schemas.tools import SendWhatsAppInput

logger = logging.getLogger("houdini.agents.whatsapp")


class WhatsAppAgent:
    """Sub-agente para WhatsApp (fase 2)."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    async def send_message(self, params: SendWhatsAppInput) -> dict:
        if not self.enabled:
            return {"error": "WhatsApp deshabilitado (fase 2). Aún no implementado."}
        # TODO: Implementar con WhatsApp Business API o Baileys
        return {"error": "No implementado aún"}

    async def send_media(self, phone: str, media_path: str) -> dict:
        if not self.enabled:
            return {"error": "WhatsApp deshabilitado (fase 2)"}
        return {"error": "No implementado aún"}
