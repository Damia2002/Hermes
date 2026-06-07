"""POST /v1/query — main research endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import QueryRequest, QueryResponse, ErrorResponse
from app.database import AgentRun, get_db
from app.flows.research_flow import run_research_flow
from app.observability.logging import get_logger
from app.safety.injection import validate_user_input
from app.safety.permissions import ExecutionContext

router = APIRouter(prefix="/v1", tags=["query"])
logger = get_logger(__name__)


def _demo_context(user_id: str, session_id: str) -> ExecutionContext:
    return ExecutionContext.from_roles(user_id=user_id, session_id=session_id, roles=["analyst"])


@router.post("/query", response_model=QueryResponse, responses={400: {"model": ErrorResponse}})
async def post_query(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    try:
        validate_user_input(req.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "validation_error", "message": str(exc)})

    ctx = _demo_context(req.user_id, req.session_id)

    run = AgentRun(
        session_id=req.session_id,
        user_id=req.user_id,
        workflow="pending",
        question=req.question,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        result = await run_research_flow(
            question=req.question,
            context=ctx,
            source_types=req.source_types or None,
            response_mode=req.response_mode,
        )
        run.status = "completed"
        run.result = result
        run.workflow = result.get("workflow", "SEARCH")
        run.latency_ms = result.get("latency_ms")
        await db.commit()
        return QueryResponse(**result)
    except Exception as exc:
        run.status = "error"
        run.error = str(exc)
        await db.commit()
        logger.error("query_failed", run_id=run.id, error=str(exc))

        err_str = str(exc)
        if "rate_limit_exceeded" in err_str or "RateLimitError" in err_str:
            import re
            retry_match = re.search(r"try again in ([\d]+m[\d.]+s|[\d.]+s)", err_str)
            retry_hint = retry_match.group(1) if retry_match else "a few minutes"
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "rate_limit_exceeded",
                    "message": f"Groq API daily token limit reached. Please try again in {retry_hint}.",
                    "retry_after": retry_hint,
                },
            )
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": err_str})


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Run not found"})
    return {
        "id": run.id,
        "session_id": run.session_id,
        "user_id": run.user_id,
        "workflow": run.workflow,
        "question": run.question,
        "status": run.status,
        "result": run.result,
        "error": run.error,
        "latency_ms": run.latency_ms,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
