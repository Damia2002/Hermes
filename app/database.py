"""SQLAlchemy async database setup and ORM models."""

import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    workflow: Mapped[str] = mapped_column(String)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    langfuse_trace_id: Mapped[str | None] = mapped_column(String, nullable=True)


class MonitorRule(Base):
    __tablename__ = "monitor_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    query: Mapped[str] = mapped_column(Text)
    source_types: Mapped[list] = mapped_column(JSON, default=list)
    schedule_cron: Mapped[str] = mapped_column(String, default="0 * * * *")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MonitorSnapshot(Base):
    __tablename__ = "monitor_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("monitor_rules.id"))
    doc_ids: Mapped[list] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProposedAction(Base):
    __tablename__ = "proposed_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("agent_runs.id"))
    user_id: Mapped[str] = mapped_column(String, index=True)
    tool_name: Mapped[str] = mapped_column(String)
    tool_input: Mapped[dict] = mapped_column(JSON)
    supporting_doc_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="pending")
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    memory_type: Mapped[str] = mapped_column(String, default="episodic")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_label: Mapped[str] = mapped_column(String, index=True)
    question_id: Mapped[str] = mapped_column(String)
    question: Mapped[str] = mapped_column(Text)
    predicted_answer: Mapped[str] = mapped_column(Text)
    gold_answer: Mapped[str] = mapped_column(Text)
    answer_correctness: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    document_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
