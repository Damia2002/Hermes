"""Action workflow: bounded ReAct loop → draft → human approval gate."""

import time
import uuid
from typing import Any

from crewai import Crew, Process, Task

from app.agents.action_agent import build_action_agent
from app.config import get_settings
from app.observability.logging import get_logger
from app.safety.permissions import ExecutionContext

settings = get_settings()
logger = get_logger(__name__)


async def run_action_flow(
    instruction: str,
    context: ExecutionContext,
    supporting_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Plan and create a draft action, then return it for human approval."""
    run_id = str(uuid.uuid4())
    start = time.monotonic()
    doc_ids = supporting_doc_ids or []

    logger.info("action_flow_start", run_id=run_id, user=context.user_id)

    action_agent = build_action_agent()
    task = Task(
        description=(
            f"The user requests the following action: {instruction!r}\n\n"
            f"Supporting document IDs: {doc_ids}\n\n"
            f"Create a draft using the appropriate tool. "
            f"Do NOT execute any real write operations. "
            f"Produce a draft that requires human approval. "
            f"Stay within {settings.max_tool_calls} tool calls."
        ),
        expected_output=(
            "A draft action (Jira issue / email / note) with its draft_id, "
            "a summary of what it will do, and a statement that it awaits human approval."
        ),
        agent=action_agent,
    )

    crew = Crew(agents=[action_agent], tasks=[task], process=Process.sequential, verbose=False)
    result = await crew.kickoff_async()
    result_text = str(result)

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info("action_flow_done", run_id=run_id, latency_ms=latency_ms)

    return {
        "run_id": run_id,
        "instruction": instruction,
        "draft": result_text,
        "supporting_doc_ids": doc_ids,
        "status": "pending_approval",
        "latency_ms": latency_ms,
        "requires_approval": True,
    }
