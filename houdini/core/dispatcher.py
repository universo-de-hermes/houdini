"""
Houdini - Dispatcher de Tools
Recibe tool calls del orquestador y los enruta al sub-agente correspondiente.
"""
import logging
from typing import Any
from schemas.tools import TOOL_REGISTRY, ToolCategory

logger = logging.getLogger("houdini.core.dispatcher")


class ToolDispatcher:
    """Enruta tool calls a los sub-agentes correspondientes."""

    def __init__(self):
        self._handlers: dict[str, Any] = {}  # tool_name -> callable
        self._agents: dict[ToolCategory, Any] = {}  # category -> agent instance

    def register_agent(self, category: ToolCategory, agent: Any):
        """Registra un sub-agente para una categoría."""
        self._agents[category] = agent
        logger.info(f"Agente registrado: {category.value}")

    def register_tool(self, tool_name: str, handler: Any):
        """Registra un handler directo para un tool específico."""
        self._handlers[tool_name] = handler

    async def dispatch(
        self, tool_name: str, args: dict, session_id: str = "default"
    ) -> dict:
        """
        Ejecuta un tool call.
        1. Busca el tool en el registry
        2. Valida args con el schema Pydantic
        3. Obtiene el handler del agente correspondiente
        4. Ejecuta y retorna resultado
        """
        if tool_name not in TOOL_REGISTRY:
            return {"error": f"Tool '{tool_name}' no encontrado"}

        spec = TOOL_REGISTRY[tool_name]
        category = spec["category"]
        input_model = spec["input_model"]

        # Validar argumentos
        try:
            validated = input_model(**args)
        except Exception as e:
            return {"error": f"Args inválidos para {tool_name}: {e}"}

        # Buscar handler
        handler = self._handlers.get(tool_name)
        if handler is None:
            # Buscar en el agente de la categoría
            agent = self._agents.get(category)
            if agent is None:
                return {"error": f"Agente {category.value} no registrado"}
            handler = getattr(agent, tool_name, None)

        if handler is None:
            return {"error": f"Handler para {tool_name} no encontrado"}

        # Ejecutar
        try:
            if callable(handler):
                result = handler(validated)
                if hasattr(result, "__await__"):
                    result = await result
                return {"ok": True, "data": result}
            return {"error": f"Handler para {tool_name} no es callable"}
        except Exception as e:
            logger.error(f"Error ejecutando {tool_name}: {e}", exc_info=True)
            return {"error": str(e)}
