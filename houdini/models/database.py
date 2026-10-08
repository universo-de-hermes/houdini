"""
Houdini - Modelos de Base de Datos
5 tipos de memoria: episódica, semántica, procedimental, tareas, documentos
"""
import uuid
import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Text, Float, DateTime, JSON,
    ForeignKey, Boolean, Index
)
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ──────────────────────────────────────────────
# 1. MEMORIA EPISÓDICA - Conversaciones
# ──────────────────────────────────────────────
class Conversation(Base):
    """Memoria episódica: conversaciones user/assistant con embeddings."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant | system | tool
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    tokens = Column(Integer, default=0)
    meta_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_conversations_session", "session_id"),
        Index("idx_conversations_created", "created_at"),
    )


# ──────────────────────────────────────────────
# 2. MEMORIA SEMÁNTICA - Hechos y preferencias
# ──────────────────────────────────────────────
class SemanticFact(Base):
    """Memoria semántica: hechos, preferencias, contactos, patrones."""
    __tablename__ = "semantic_facts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    subject = Column(String(255), nullable=False)    # ej: "usuario"
    predicate = Column(String(255), nullable=False)   # ej: "prefiere_reuniones"
    object_value = Column(Text, nullable=True)        # ej: "por_la_mañana"
    confidence = Column(Float, default=1.0)
    source = Column(String(255), default="inferred")  # inferred | explicit | learned
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_facts_subject", "subject"),
    )


# ──────────────────────────────────────────────
# 3. MEMORIA PROCEDIMENTAL - Skills aprendidas
# ──────────────────────────────────────────────
class Procedure(Base):
    """Memoria procedimental: skills, workflows recurrentes."""
    __tablename__ = "procedures"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    steps_json = Column(JSON, default=list)          # lista de pasos
    trigger_pattern = Column(Text, nullable=True)     # regex o descripción natural
    embedding = Column(Vector(384), nullable=True)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ──────────────────────────────────────────────
# 4. ESTADO DE TAREAS - Workflows multi-paso
# ──────────────────────────────────────────────
class TaskState(Base):
    """Estado de tareas en curso: workflows multi-paso."""
    __tablename__ = "task_states"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    task_type = Column(String(100), nullable=False)   # ej: "send_email_and_log"
    status = Column(String(50), default="pending")     # pending | running | completed | failed
    context_json = Column(JSON, default=dict)         # datos contextuales
    current_step = Column(Integer, default=0)
    parent_task_id = Column(UUID(as_uuid=False), ForeignKey("task_states.id"), nullable=True)
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    parent = relationship("TaskState", remote_side="TaskState.id", backref="subtasks")

    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_type", "task_type"),
    )


# ──────────────────────────────────────────────
# 5. DOCUMENTOS - RAG / Drive indexado
# ──────────────────────────────────────────────
class Document(Base):
    """Embeddings de documentos para RAG (PDFs, notas, archivos Drive)."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    source_type = Column(String(50), nullable=False)  # drive | local | pdf | note
    source_id = Column(String(255), nullable=True)    # ID en Drive o path local
    title = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True)  # sha256 para dedup
    chunks_json = Column(JSON, default=list)          # lista de chunks de texto
    embeddings = Column(JSON, default=list)           # lista de vectores (uno por chunk)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_docs_source", "source_type", "source_id"),
        Index("idx_docs_hash", "content_hash"),
    )


# ──────────────────────────────────────────────
# 6. RECORDATORIOS / NOTIFICACIONES PROGRAMADAS
# ──────────────────────────────────────────────
class Reminder(Base):
    """Recordatorios programados via Telegram."""
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    chat_id = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    run_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")    # pending | sent | cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_reminders_run_at", "run_at", "status"),
    )
