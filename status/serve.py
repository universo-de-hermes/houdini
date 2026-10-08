"""
Status Server + Static Files — Sirve el Command Center y la API en un solo puerto.
"""
import json
import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from status.tracker import get_all_status, get_agent_status, update_agent_status, DEFAULT_STATUS

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Metaverso — Command Center")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Endpoints ──

class StatusUpdate(BaseModel):
    doing: Optional[str] = None
    task: Optional[str] = None
    status: Optional[str] = None
    walk_x: Optional[float] = None
    walk_z: Optional[float] = None

@app.get("/api/status")
def get_status():
    return get_all_status()

@app.get("/api/status/{agent_id}")
def get_single_agent(agent_id: str):
    s = get_agent_status(agent_id)
    if s is None:
        raise HTTPException(404, f"Agente '{agent_id}' no encontrado")
    return s

@app.post("/api/status/{agent_id}")
def post_status(agent_id: str, update: StatusUpdate):
    if agent_id not in DEFAULT_STATUS:
        raise HTTPException(404, f"Agente '{agent_id}' no registrado")
    fields = {}
    if update.doing is not None: fields["doing"] = update.doing
    if update.task is not None: fields["task"] = update.task
    if update.status is not None: fields["status"] = update.status
    if update.walk_x is not None: fields["walk_x"] = update.walk_x
    if update.walk_z is not None: fields["walk_z"] = update.walk_z
    if fields:
        update_agent_status(agent_id, **fields)
    return {"ok": True, "agent_id": agent_id, "updated": fields}

@app.get("/health")
def health():
    return {"status": "ok", "service": "universo-hermes"}

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"\n{'='*50}")
    print(f"  🏢  UNIVERSO DE JUANJO — COMMAND CENTER")
    print(f"{'='*50}")
    print(f"  🌐  http://localhost:{port}              → Edificio 3D")
    print(f"  📡  http://localhost:{port}/api/status    → API de estado")
    print(f"  ❤️   http://localhost:{port}/health       → Health check")
    print(f"{'='*50}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)