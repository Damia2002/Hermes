"""Action approval/rejection endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ActionApprove
from app.database import AuditEvent, ProposedAction, get_db
from app.observability.logging import get_logger

router = APIRouter(prefix="/v1/actions", tags=["actions"])
logger = get_logger(__name__)


@router.get("")
async def list_actions(user_id: str = "demo-user", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProposedAction).where(ProposedAction.user_id == user_id))
    actions = result.scalars().all()
    return [
        {
            "id": a.id,
            "tool_name": a.tool_name,
            "tool_input": a.tool_input,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in actions
    ]


@router.post("/{action_id}/approve", status_code=200)
async def decide_action(action_id: str, req: ActionApprove, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProposedAction).where(ProposedAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Action not found"})
    if action.status != "pending":
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": f"Action already {action.status}"})

    action.status = "approved" if req.decision == "approve" else "rejected"
    action.approved_by = req.user_id
    action.decided_at = datetime.utcnow()

    audit = AuditEvent(
        run_id=action.run_id,
        user_id=req.user_id,
        event_type=f"action_{req.decision}d",
        payload={"action_id": action_id, "tool": action.tool_name, "note": req.note},
    )
    db.add(audit)
    await db.commit()

    logger.info("action_decided", action_id=action_id, decision=req.decision, user=req.user_id)
    return {"action_id": action_id, "status": action.status}
