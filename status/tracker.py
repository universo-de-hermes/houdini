"""
Status Tracker — Módulo compartido de estado en vivo para Universo Hermes.
Almacena el estado actual de cada agente en memoria.
Thread-safe para uso concurrente con asyncio.
"""
import json
import os
import threading
from datetime import datetime
from typing import Optional

# ── Ruta del archivo de estado (persistente para que el server lo lea) ──
_STATUS_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(_STATUS_DIR, "agent_status.json")

_lock = threading.Lock()

# ── Estado por defecto de cada agente ──
DEFAULT_STATUS = {
    "houdini": {
            "name": "HOUDINI",
            "doing": "En espera",
            "task": "Esperando órdenes del jefe",
            "status": "idle",
            "color": "#6C3BD2",
            "team": "GERENCIA",
            "walk_x": None,
            "walk_z": None,
            "updated_at": None,
        },
    "gmail": {
        "name": "GMAIL AGENT",
        "doing": "En espera",
        "task": "Monitoreando bandeja de entrada",
        "status": "idle",
        "color": "#4285F4",
        "team": "COMUNICACIÓN",
        "updated_at": None,
    },
    "telegram": {
        "name": "TELEGRAM AGENT",
        "doing": "En espera",
        "task": "Canal activo, sin novedades",
        "status": "idle",
        "color": "#45C4F5",
        "team": "COMUNICACIÓN",
        "updated_at": None,
    },
    "tts": {
        "name": "TTS AGENT",
        "doing": "En espera",
        "task": "Sintetizador en reposo",
        "status": "idle",
        "color": "#E6E6FA",
        "team": "COMUNICACIÓN",
        "updated_at": None,
    },
    "whatsapp2": {
        "name": "WHATSAPP AGENT",
        "doing": "No operativo",
        "task": "Fase 2 — pendiente de implementación",
        "status": "off",
        "color": "#7A8090",
        "team": "COMUNICACIÓN",
        "updated_at": None,
    },
    "sheets": {
        "name": "SHEETS AGENT",
        "doing": "En espera",
        "task": "Hojas de cálculo sincronizadas",
        "status": "idle",
        "color": "#B0E0E6",
        "team": "DATOS",
        "updated_at": None,
    },
    "drive": {
        "name": "DRIVE AGENT",
        "doing": "En espera",
        "task": "Archivos sincronizados",
        "status": "idle",
        "color": "#FFD400",
        "team": "DATOS",
        "updated_at": None,
    },
    "calendar": {
        "name": "CALENDAR AGENT",
        "doing": "En espera",
        "task": "Agenda al día",
        "status": "idle",
        "color": "#2ECC71",
        "team": "DATOS",
        "updated_at": None,
    },
    "dashboard": {
        "name": "DASHBOARD AGENT",
        "doing": "En espera",
        "task": "Métricas calculadas",
        "status": "idle",
        "color": "#FF8C1A",
        "team": "ESTUDIO",
        "updated_at": None,
    },
    "design": {
        "name": "DESIGN AGENT",
        "doing": "En espera",
        "task": "Esperando solicitud de diseño",
        "status": "idle",
        "color": "#FF6FB5",
        "team": "ESTUDIO",
        "updated_at": None,
    },
    "recep": {
        "name": "RECEPCIONISTA BOT",
        "doing": "En espera",
        "task": "Esperando mensajes de clientes",
        "status": "idle",
        "color": "#B8860B",
        "team": "LOBBY",
        "updated_at": None,
    },
    "recep-cal": {
        "name": "CALENDAR AGENT",
        "doing": "En espera",
        "task": "Sin solicitudes de agenda",
        "status": "idle",
        "color": "#2ECC71",
        "team": "LOBBY",
        "updated_at": None,
    },
    "wa-sender": {
        "name": "WHATSAPP SENDER",
        "doing": "En espera",
        "task": "Bandeja de salida vacía",
        "status": "idle",
        "color": "#128C7E",
        "team": "LOBBY",
        "updated_at": None,
    },
    "handoff": {
        "name": "HUMAN HANDOFF",
        "doing": "En espera",
        "task": "Sin casos para escalar",
        "status": "idle",
        "color": "#C2C8D6",
        "team": "LOBBY",
        "updated_at": None,
    },
}


def get_all_status() -> dict:
    """Obtiene el estado completo de todos los agentes."""
    with _lock:
        return _load().copy()


def get_agent_status(agent_id: str) -> Optional[dict]:
    """Obtiene el estado de un agente específico."""
    with _lock:
        data = _load()
        return data.get(agent_id)


def update_agent_status(agent_id: str, **fields):
    """
    Actualiza campos específicos del estado de un agente.
    
    Args:
        agent_id: ID del agente (ej: 'houdini', 'gmail')
        **fields: Campos a actualizar (doing, task, status, etc.)
    """
    with _lock:
        data = _load()
        if agent_id not in data:
            data[agent_id] = DEFAULT_STATUS.get(agent_id, {})
        data[agent_id].update(fields)
        data[agent_id]["updated_at"] = datetime.now().isoformat()
        _save(data)


def _load() -> dict:
    """Carga el estado desde el archivo JSON."""
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_STATUS.copy()


def _save(data: dict):
    """Guarda el estado en el archivo JSON."""
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Inicializar estado al importar ──
if not os.path.exists(STATUS_FILE):
    _save(DEFAULT_STATUS)