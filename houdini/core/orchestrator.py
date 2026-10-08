"""
Houdini - Orquestador Principal
Recibe la intención del usuario, decide si es simple o compleja,
y delega a sub-agentes via function calling.
Usa DeepSeek V4 Pro (OpenRouter) como primario, GPT-4o como fallback.
"""
import json
import logging
import datetime
import asyncio
from typing import Any, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel

from config.settings import get_settings
from schemas.tools import TOOL_REGISTRY

# ── Estado en vivo para Command Center ──
import sys as _sys
_sys.path.insert(0, __file__[:__file__.rfind("houdini")])
try:
    from status.tracker import update_agent_status, get_agent_status
    _STATUS_OK = True
except ImportError:
    _STATUS_OK = False
    def update_agent_status(*a, **kw): pass
    def get_agent_status(*a, **kw): return {}

logger = logging.getLogger("houdini.core.orchestrator")
settings = get_settings()


class OrchestratorResponse(BaseModel):
    text: str
    tool_calls_made: list[dict] = []
    error: Optional[str] = None


class HoudiniOrchestrator:
    """
    Orquestador a medida:
    - DeepSeek V4 Pro (OpenRouter) con function calling
    - Fallback a GPT-4o (OpenRouter)
    """

    SYSTEM_PROMPT = """Eres Houdini, un asistente personal con estilo de mayordomo elegante y eficiente.
Hablas en español con un tono formal pero cercano — tratas al usuario como "jefe".
NUNCA saludes con "buenos días", "buenas tardes" ni "buenas noches". Saluda solo con "🎩" o directamente con lo que el usuario necesita.
Eres como un mayordomo británico latino: cortés, preciso, con un toque de distinción.

Tienes acceso a herramientas para:

📧 CORREO (send_email, search_emails, read_email)
📅 CALENDARIO (create_event, list_events, update_event, find_free_slots)
📊 SHEETS (read_range, write_range)
☁️ DRIVE (upload_file, search_files, download_file)
📱 TELEGRAM (send_message, schedule_reminder)
🎙️ VOZ (speak)
🎨 DISEÑO (create_html, list_templates)
📈 DASHBOARD (send_dashboard)
💬 WHATSAPP (send_whatsapp)
🎵 SPOTIFY (spotify_play, spotify_control, spotify_volume)

IMPORTANTE:
- Cuando necesites usar una herramienta, responde primero con un mensaje corto y amable al usuario explicando qué vas a hacer, y LUEGO usa la herramienta.
- Siempre confirma al usuario cuando una acción se complete exitosamente.
- Si algo falla, explícale con honestidad pero sin alarmar.
- Fecha actual: """

    PLAN_PROMPT = """
Para tareas complejas, desglosa en pasos usando este formato:
📋 PLAN:
1. [Primer paso] → herramienta()
2. [Segundo paso] → herramienta()
3. [Tercer paso] → herramienta()
Luego ejecuta cada paso secuencialmente usando function calling.
"""

    def __init__(self):
        # Cliente OpenRouter (OpenAI-compatible)
        self.client = None
        if settings.openrouter_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            )
            logger.info(f"✅ OpenRouter configurado: {settings.openrouter_model}")

        self._tool_executor = None
        self._http_session = None

    def set_tool_executor(self, executor):
        """Inyecta el ejecutor de tools (ToolDispatcher)."""
        self._tool_executor = executor

    def _fire_3d_flow_sync(self, user_text: str):
        """Dispara el flujo en el Command Center 3D."""
        try:
            import json, os
            status_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "status")
            status_file = os.path.join(status_dir, "agent_status.json")

            if os.path.exists(status_file):
                with open(status_file) as f:
                    data = json.load(f)
                if "houdini" in data:
                    data["houdini"]["doing"] = f"Procesando: {user_text[:40]}"
                    data["houdini"]["task"] = user_text[:80]
                    data["houdini"]["status"] = "active"
                    with open(status_file, "w") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    logger.info(f"🎬 3D: Houdini marcado activo en JSON compartido")
                try:
                    import requests
                    requests.post("http://localhost:3000/api/fire", json={"text": user_text}, timeout=1)
                except:
                    pass
        except Exception as e:
            logger.debug(f"3D fallback: {e}")

    def _build_openai_tools(self) -> list[dict]:
        """Construye tools en formato OpenAI function calling."""
        tools = []
        for name, spec in TOOL_REGISTRY.items():
            schema = spec["input_model"].model_json_schema()
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": spec["description"],
                    "parameters": schema,
                }
            })
        return tools

    async def orchestrate(
        self,
        user_text: str,
        session_id: str = "default",
        context: list[dict] | None = None,
        force_plan: bool = False,
    ) -> OrchestratorResponse:
        """
        Punto de entrada principal.
        1. Construye mensajes con contexto + memoria
        2. Detecta si necesita plan
        3. Llama a OpenRouter (DeepSeek V4 Pro) con function calling
        4. Ejecuta tool calls si los hay
        5. Retorna respuesta final
        """
        needs_plan = force_plan or self._detect_complex_task(user_text)

        # ── Reportar estado en vivo ──
        update_agent_status("houdini", doing="Procesando solicitud", task=user_text[:80], status="active")
        update_agent_status("houdini", doing="Orquestando con DeepSeek V4 Pro", status="active")

        now = datetime.datetime.now()
        today_str = now.strftime("%A, %d de %B de %Y")
        system_prompt = self.SYSTEM_PROMPT + today_str + ". Son las " + now.strftime("%H:%M") + "."

        if not self.client:
            return OrchestratorResponse(
                text="⚠️ No hay conexión con OpenRouter. Revisa la configuración.",
                error="OPENROUTER_API_KEY no configurada",
            )

        return await self._orchestrate_openrouter(
            user_text, system_prompt, needs_plan, context, session_id
        )

    async def _orchestrate_openrouter(
        self, user_text, system_prompt, needs_plan, context, session_id
    ) -> OrchestratorResponse:
        """Usa DeepSeek V4 Pro con function calling vía OpenRouter."""

        # 🎬 DISPARAR 3D
        import threading
        threading.Thread(target=self._fire_3d_flow_sync, args=(user_text,), daemon=True).start()

        messages = []
        if context:
            for msg in context:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_text})

        tools = self._build_openai_tools()
        tool_calls_made = []

        system_content = system_prompt
        if needs_plan:
            system_content += "\n\n" + self.PLAN_PROMPT

        # Primera llamada al modelo
        response = await self.client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": system_content},
                *messages
            ],
            tools=tools if tools else [],
            max_tokens=4096,
            extra_headers={
                "HTTP-Referer": "https://github.com/houdini",
                "X-Title": "Houdini Assistant",
            },
        )

        message = response.choices[0].message

        # Si no hay tool calls, respuesta directa
        if not message.tool_calls:
            return OrchestratorResponse(
                text=message.content or "",
                tool_calls_made=tool_calls_made,
            )

        # Hay tool calls → manejarlas
        return await self._handle_openrouter_tool_calls(
            message, messages, tools, system_content, tool_calls_made, session_id, user_text
        )

    async def _handle_openrouter_tool_calls(
        self, message, messages, tools, system_content, tool_calls_made, session_id, user_text
    ) -> OrchestratorResponse:
        """Ejecuta tool calls de OpenRouter y continúa el loop."""

        # Añadir mensaje del asistente con tool_calls
        assistant_msg = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in message.tool_calls
            ]
        }
        messages.append(assistant_msg)

        # Procesar cada tool call
        for tc in message.tool_calls:
            tool_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}

            tool_call_id = tc.id

            logger.info(f"Tool call: {tool_name}({args})")

            # ── Reportar estado en vivo del sub-agente ──
            _agent_map = {
                "send_email":"gmail","search_emails":"gmail","read_email":"gmail",
                "create_event":"calendar","list_events":"calendar","update_event":"calendar","find_free_slots":"calendar",
                "read_range":"sheets","write_range":"sheets",
                "upload_file":"drive","search_files":"drive","download_file":"drive",
                "send_message":"telegram","schedule_reminder":"telegram",
                "speak":"tts",
                "create_html":"design","list_templates":"design",
                "send_dashboard":"dashboard",
                "send_whatsapp":"whatsapp2",
                "spotify_play":"spotify","spotify_control":"spotify","spotify_volume":"spotify",
            }
            aid = _agent_map.get(tool_name)
            if aid:
                update_agent_status(aid, doing=f"Ejecutando {tool_name}", task=str(args)[:80], status="active")
                _desk_positions = {
                    "gmail":[-13, -6.6], "telegram":[-9.4, -2.2], "tts":[-13.4, -1.2], "whatsapp2":[-8.6, -6.9],
                    "sheets":[13, -6.6], "drive":[9.4, -2.2], "calendar":[13.4, -1.2],
                    "dashboard":[9.6, 7.4], "design":[13.4, 8.2],
                    "recep_recep":[0, -2.4], "recep_cal":[-6.6, 3.2], "wa_sender":[6.6, 3.2], "handoff":[-11, -3.4],
                }
                desk_pos = _desk_positions.get(aid)
                if desk_pos:
                    update_agent_status("houdini", doing=f"Caminando hacia {aid}", walk_x=desk_pos[0], walk_z=desk_pos[1])

            result = None
            if self._tool_executor:
                result = await self._tool_executor.dispatch(tool_name, args, session_id)
            else:
                result = {"error": "Tool executor no configurado"}

            tool_calls_made.append({
                "tool": tool_name,
                "args": args,
                "result": result,
            })

            # Añadir resultado en formato OpenAI tool
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

        # Segunda llamada al modelo para respuesta final
        response = await self.client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": system_content},
                *messages
            ],
            tools=tools if tools else [],
            max_tokens=4096,
            extra_headers={
                "HTTP-Referer": "https://github.com/houdini",
                "X-Title": "Houdini Assistant",
            },
        )

        message = response.choices[0].message

        # Si hay más tool calls, recursión
        if message.tool_calls:
            return await self._handle_openrouter_tool_calls(
                message, messages, tools, system_content, tool_calls_made, session_id, user_text
            )

        # Respuesta final
        return OrchestratorResponse(
            text=message.content or "",
            tool_calls_made=tool_calls_made,
        )

    def _detect_complex_task(self, text: str) -> bool:
        """Heurística simple para detectar tareas complejas."""
        complex_keywords = [
            "varios", "primero", "luego", "después", "paso a paso",
            "compara", "investiga", "analiza", "cada", "todos",
            "y también", "además", "plan", "agenda",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in complex_keywords)