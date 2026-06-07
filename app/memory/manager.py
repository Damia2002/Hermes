"""Memory manager: CRUD for episodic, semantic, and procedural memory entries."""

import json
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import MemoryEntry
from app.memory.models import MemoryEntryCreate, MemoryEntryRead
from app.observability.logging import get_logger

logger = get_logger(__name__)

MEMORY_TYPES = {"episodic", "semantic", "procedural"}


async def create_memory(db: AsyncSession, entry: MemoryEntryCreate) -> MemoryEntryRead:
    if entry.memory_type not in MEMORY_TYPES:
        raise ValueError(f"Invalid memory_type {entry.memory_type!r}. Must be one of {MEMORY_TYPES}.")

    row = MemoryEntry(
        user_id=entry.user_id,
        content=entry.content,
        memory_type=entry.memory_type,
        tags=entry.tags,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("memory_created", id=row.id, type=entry.memory_type, user=entry.user_id)
    return _to_read(row)


async def list_memory(db: AsyncSession, user_id: str, memory_type: str | None = None) -> list[MemoryEntryRead]:
    stmt = select(MemoryEntry).where(MemoryEntry.user_id == user_id)
    if memory_type:
        stmt = stmt.where(MemoryEntry.memory_type == memory_type)
    stmt = stmt.order_by(MemoryEntry.created_at.desc())
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_read(r) for r in rows]


async def delete_memory(db: AsyncSession, memory_id: str, user_id: str) -> bool:
    stmt = delete(MemoryEntry).where(MemoryEntry.id == memory_id, MemoryEntry.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("memory_deleted", id=memory_id, user=user_id)
    return deleted


def _to_read(row: MemoryEntry) -> MemoryEntryRead:
    return MemoryEntryRead(
        id=row.id,
        user_id=row.user_id,
        content=row.content,
        memory_type=row.memory_type,
        tags=row.tags if isinstance(row.tags, list) else json.loads(row.tags or "[]"),
        created_at=row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
    )
