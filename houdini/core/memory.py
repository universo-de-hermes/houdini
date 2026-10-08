"""
Houdini - Sistema de Memoria Persistente
Gestiona los 5 tipos de memoria en PostgreSQL + pgvector.
Usa SQLAlchemy síncrono (más simple, ideal para local/escritorio).
"""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from models.database import (
    Base, Conversation, SemanticFact, Procedure,
    TaskState, Document, Reminder
)

logger = logging.getLogger("houdini.core.memory")
settings = get_settings()


class MemoryStore:
    """Gestor central de memoria persistente (síncrono)."""

    def __init__(self):
        self.engine = create_engine(
            settings.sync_database_url,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def init_db(self):
        """Crea todas las tablas + extensión pgvector."""
        with self.engine.begin() as conn:
            # Crear extensión pgvector (si no existe)
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # Crear tablas
            Base.metadata.create_all(conn)
            logger.info("Base de datos inicializada (tablas + pgvector)")

    def close(self):
        self.engine.dispose()

    # ──────────────────────────────────────────
    # MEMORIA EPISÓDICA - Conversaciones
    # ──────────────────────────────────────────
    def save_conversation(
        self, session_id: str, role: str, content: str,
        tokens: int = 0, embedding: list[float] | None = None,
        meta: dict | None = None
    ) -> Conversation:
        with self.Session() as db:
            conv = Conversation(
                session_id=session_id,
                role=role,
                content=content,
                tokens=tokens,
                embedding=embedding,
                meta_json=meta or {},
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            logger.debug(f"Conversación guardada: {role} ({tokens} tokens)")
            return conv

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        """Obtiene historial de conversación para contexto."""
        with self.Session() as db:
            result = db.execute(
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            # Retornar en orden cronológico (oldest first)
            return [
                {"role": r.role, "content": r.content}
                for r in reversed(rows)
            ]

    def search_conversations(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        """Búsqueda semántica en conversaciones via pgvector."""
        with self.Session() as db:
            result = db.execute(
                select(
                    Conversation,
                    Conversation.embedding.cosine_distance(query_embedding).label("distance")
                )
                .where(Conversation.embedding.isnot(None))
                .order_by("distance")
                .limit(top_k)
            )
            return [
                {"content": row[0].content, "role": row[0].role, "distance": row[1]}
                for row in result.all()
            ]

    # ──────────────────────────────────────────
    # MEMORIA SEMÁNTICA - Hechos y preferencias
    # ──────────────────────────────────────────
    def save_fact(
        self, subject: str, predicate: str, object_value: str,
        confidence: float = 1.0, source: str = "explicit",
        embedding: list[float] | None = None
    ) -> SemanticFact:
        with self.Session() as db:
            fact = SemanticFact(
                subject=subject,
                predicate=predicate,
                object_value=object_value,
                confidence=confidence,
                source=source,
                embedding=embedding,
            )
            db.add(fact)
            db.commit()
            db.refresh(fact)
            logger.debug(f"Hecho guardado: {subject} {predicate} {object_value}")
            return fact

    def get_facts(self, subject: str | None = None) -> list[dict]:
        with self.Session() as db:
            query = select(SemanticFact)
            if subject:
                query = query.where(SemanticFact.subject == subject)
            result = db.execute(query)
            return [
                {
                    "subject": f.subject,
                    "predicate": f.predicate,
                    "object": f.object_value,
                    "confidence": f.confidence,
                }
                for f in result.scalars().all()
            ]

    # ──────────────────────────────────────────
    # MEMORIA PROCEDIMENTAL - Skills
    # ──────────────────────────────────────────
    def save_procedure(
        self, name: str, description: str, steps: list[dict],
        trigger_pattern: str | None = None,
        embedding: list[float] | None = None
    ) -> Procedure:
        with self.Session() as db:
            proc = Procedure(
                name=name,
                description=description,
                steps_json=steps,
                trigger_pattern=trigger_pattern,
                embedding=embedding,
            )
            db.add(proc)
            db.commit()
            db.refresh(proc)
            return proc

    def get_procedure(self, name: str) -> Optional[dict]:
        with self.Session() as db:
            result = db.execute(
                select(Procedure).where(Procedure.name == name)
            )
            proc = result.scalar_one_or_none()
            if proc:
                return {
                    "name": proc.name,
                    "description": proc.description,
                    "steps": proc.steps_json,
                    "success_count": proc.success_count,
                }
            return None

    # ──────────────────────────────────────────
    # ESTADO DE TAREAS
    # ──────────────────────────────────────────
    def create_task(
        self, task_type: str, context: dict | None = None,
        parent_task_id: str | None = None
    ) -> TaskState:
        with self.Session() as db:
            task = TaskState(
                task_type=task_type,
                context_json=context or {},
                parent_task_id=parent_task_id,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task

    def update_task(
        self, task_id: str, status: str | None = None,
        current_step: int | None = None, result: dict | None = None,
        error: str | None = None
    ):
        with self.Session() as db:
            result_q = db.execute(
                select(TaskState).where(TaskState.id == task_id)
            )
            task = result_q.scalar_one_or_none()
            if task:
                if status:
                    task.status = status
                if current_step is not None:
                    task.current_step = current_step
                if result is not None:
                    task.result_json = result
                if error is not None:
                    task.error_message = error
                task.updated_at = datetime.utcnow()
                db.commit()

    def get_pending_tasks(self) -> list[dict]:
        with self.Session() as db:
            result = db.execute(
                select(TaskState)
                .where(TaskState.status.in_(["pending", "running"]))
                .order_by(TaskState.created_at)
            )
            return [
                {
                    "id": str(t.id),
                    "type": t.task_type,
                    "status": t.status,
                    "step": t.current_step,
                }
                for t in result.scalars().all()
            ]

    # ──────────────────────────────────────────
    # DOCUMENTOS - RAG
    # ──────────────────────────────────────────
    def save_document(
        self, source_type: str, title: str, chunks: list[str],
        embeddings: list[list[float]] | None = None,
        source_id: str | None = None, content_hash: str | None = None,
        metadata: dict | None = None
    ) -> Document:
        with self.Session() as db:
            doc = Document(
                source_type=source_type,
                source_id=source_id,
                title=title,
                content_hash=content_hash,
                chunks_json=chunks,
                embeddings=embeddings,
                metadata_json=metadata or {},
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc

    def search_documents(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        with self.Session() as db:
            result = db.execute(
                select(Document).limit(top_k)
            )
            return [
                {
                    "title": d.title,
                    "source_type": d.source_type,
                    "chunks": d.chunks_json[:3],
                }
                for d in result.scalars().all()
            ]

    # ──────────────────────────────────────────
    # RECORDATORIOS
    # ──────────────────────────────────────────
    def create_reminder(
        self, chat_id: str, message: str, run_at: datetime
    ) -> Reminder:
        with self.Session() as db:
            rem = Reminder(
                chat_id=chat_id,
                message=message,
                run_at=run_at,
            )
            db.add(rem)
            db.commit()
            db.refresh(rem)
            logger.info(f"Recordatorio creado: {run_at} -> {message[:50]}")
            return rem

    def get_pending_reminders(self) -> list[Reminder]:
        with self.Session() as db:
            result = db.execute(
                select(Reminder)
                .where(
                    Reminder.status == "pending",
                    Reminder.run_at <= datetime.utcnow()
                )
                .order_by(Reminder.run_at)
            )
            return list(result.scalars().all())

    def mark_reminder_sent(self, reminder_id: str):
        with self.Session() as db:
            result = db.execute(
                select(Reminder).where(Reminder.id == reminder_id)
            )
            rem = result.scalar_one_or_none()
            if rem:
                rem.status = "sent"
                rem.sent_at = datetime.utcnow()
                db.commit()

    def cancel_reminder(self, reminder_id: str) -> bool:
        with self.Session() as db:
            result = db.execute(
                select(Reminder).where(Reminder.id == reminder_id)
            )
            rem = result.scalar_one_or_none()
            if rem and rem.status == "pending":
                rem.status = "cancelled"
                db.commit()
                return True
            return False

    @property
    def database_url(self) -> str:
        """URL de base de datos síncrona para APScheduler."""
        return settings.sync_database_url