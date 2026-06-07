"""Monitoring workflow: scheduled retrieval comparison and change alerting."""

import time
from datetime import datetime
from typing import Any

from crewai import Crew, Process, Task

from app.agents.monitor import build_monitor
from app.config import get_settings
from app.observability.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

CHANGE_TYPES = ["NEW_INFORMATION", "CHANGED_INFORMATION", "DOCUMENT_REMOVED", "NO_MATERIAL_CHANGE", "CONFLICT_DETECTED"]


async def run_monitoring_flow(rule: dict[str, Any], previous_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a single monitoring rule and return the change report."""
    start = time.monotonic()
    query = rule["query"]
    rule_id = rule["id"]
    prev_doc_ids = previous_snapshot.get("doc_ids", []) if previous_snapshot else []

    logger.info("monitoring_flow_start", rule_id=rule_id, query=query[:60])

    monitor_agent = build_monitor()
    prev_ids_str = ",".join(prev_doc_ids) if prev_doc_ids else "none"

    task = Task(
        description=(
            f"Run this monitoring query: {query!r}\n\n"
            f"Previous snapshot doc_ids: {prev_ids_str}\n\n"
            "Use compare_knowledge_snapshots to determine if information has changed. "
            "Classify the change and write a concise alert report. "
            "Only flag a change if it is material (not cosmetic)."
        ),
        expected_output=(
            "Change type (one of: NEW_INFORMATION, CHANGED_INFORMATION, DOCUMENT_REMOVED, "
            "NO_MATERIAL_CHANGE, CONFLICT_DETECTED) followed by a 2–5 sentence change report."
        ),
        agent=monitor_agent,
    )

    crew = Crew(agents=[monitor_agent], tasks=[task], process=Process.sequential, verbose=False)
    result = await crew.kickoff_async()
    result_text = str(result)

    change_type = "NO_MATERIAL_CHANGE"
    for ct in CHANGE_TYPES:
        if ct in result_text.upper():
            change_type = ct
            break

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info("monitoring_flow_done", rule_id=rule_id, change_type=change_type, latency_ms=latency_ms)

    return {
        "rule_id": rule_id,
        "query": query,
        "change_type": change_type,
        "summary": result_text,
        "checked_at": datetime.utcnow().isoformat(),
        "latency_ms": latency_ms,
        "material_change": change_type != "NO_MATERIAL_CHANGE",
    }
