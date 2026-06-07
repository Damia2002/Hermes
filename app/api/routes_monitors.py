"""Monitor CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MonitorCreate
from app.database import MonitorRule, get_db

router = APIRouter(prefix="/v1/monitors", tags=["monitors"])


@router.post("", status_code=201)
async def create_monitor(req: MonitorCreate, db: AsyncSession = Depends(get_db)):
    rule = MonitorRule(
        user_id=req.user_id,
        name=req.name,
        query=req.query,
        source_types=req.source_types,
        schedule_cron=req.schedule_cron,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "status": "created"}


@router.get("")
async def list_monitors(user_id: str = "demo-user", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MonitorRule).where(MonitorRule.user_id == user_id))
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "query": r.query,
            "source_types": r.source_types,
            "schedule_cron": r.schedule_cron,
            "is_active": r.is_active,
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
        }
        for r in rules
    ]


@router.delete("/{monitor_id}", status_code=204)
async def delete_monitor(monitor_id: str, user_id: str = "demo-user", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        delete(MonitorRule).where(MonitorRule.id == monitor_id, MonitorRule.user_id == user_id)
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Monitor not found"})
