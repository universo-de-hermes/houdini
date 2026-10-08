"""
Status Server — API REST para el estado en vivo de Universo Hermes.
Sirve datos al Command Center 3D via HTTP.
"""
import json
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Asegurar que podemos importar el módulo status
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from status.tracker import get_all_status, get_agent_status, update_agent_status, DEFAULT_STATUS

app = FastAPI(title="Universo Hermes — Status API")

# CORS: permitir que el Command Center (cualquier origen) consulte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatusUpdate(BaseModel):
    doing: Optional[str] = None
    task: Optional[str] = None
    status: Optional[str] = None  # 'active', 'idle', 'off'


@app.get("/api/status")
def get_status():
    """Devuelve el estado de TODOS los agentes."""
    return get_all_status()


@app.get("/api/status/{agent_id}")
def get_single_agent(agent_id: str):
    """Devuelve el estado de UN agente."""
    status = get_agent_status(agent_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")
    return status


@app.post("/api/status/{agent_id}")
def post_status(agent_id: str, update: StatusUpdate):
    """Actualiza el estado de un agente (usado por los bots)."""
    if agent_id not in DEFAULT_STATUS:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no registrado")
    
    fields = {}
    if update.doing is not None:
        fields["doing"] = update.doing
    if update.task is not None:
        fields["task"] = update.task
    if update.status is not None:
        fields["status"] = update.status
    
    if fields:
        update_agent_status(agent_id, **fields)
    
    return {"ok": True, "agent_id": agent_id, "updated": fields}


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok", "service": "universo-hermes-status"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("STATUS_PORT", 8765))
    print(f"🚀 Status API corriendo en http://localhost:{port}")
    print(f"📡 Endpoints:")
    print(f"   GET  /api/status           → Estado completo")
    print(f"   GET  /api/status/houdini    → Estado de un agente")
    print(f"   POST /api/status/houdini    → Actualizar estado")
    print(f"   GET  /health                → Health check")
    uvicorn.run(app, host="0.0.0.0", port=port)