"""Research workflow: classify → plan → retrieve → analyse → verify."""

import time
import uuid
from typing import Any

from crewai import Crew, Process, Task

from app.agents.analyst import build_analyst
from app.agents.planner import build_planner
from app.agents.retriever import build_retriever
from app.agents.verifier import build_verifier
from app.config import get_settings
from app.observability.logging import get_logger
from app.observability.tracing import trace_workflow
from app.rag.context_builder import build_context
from app.rag.hybrid_retriever import hybrid_search
from app.rag.reranker import rerank
from app.safety.injection import validate_user_input
from app.safety.permissions import ExecutionContext

settings = get_settings()
logger = get_logger(__name__)


def classify_request(question: str) -> str:
    """Lightweight classification using keyword heuristics (before LLM call)."""
    q = question.lower()
    if any(k in q for k in ["monitor", "alert", "notify", "watch", "track changes"]):
        return "MONITOR"
    if any(k in q for k in ["create", "write", "send", "draft", "submit", "open ticket"]):
        return "ACTION"
    if any(k in q for k in ["compare", "conflict", "synthesise", "cross", "multiple sources", "all teams"]):
        return "RESEARCH"
    return "SEARCH"


async def run_research_flow(
    question: str,
    context: ExecutionContext,
    source_types: list[str] | None = None,
    response_mode: str = "detailed",
) -> dict[str, Any]:
    """Main research orchestration. Returns a structured response dict."""
    run_id = str(uuid.uuid4())
    start = time.monotonic()

    safe_q = validate_user_input(question)
    workflow = classify_request(safe_q)
    logger.info("flow_start", run_id=run_id, workflow=workflow, user=context.user_id)

    with trace_workflow(name=f"research:{workflow}", user_id=context.user_id, metadata={"run_id": run_id}) as trace:
        # ── Step 1: Retrieval ────────────────────────────────────────────────
        raw_docs = hybrid_search(
            query=safe_q,
            top_k=settings.max_retrieved_documents,
            source_types=source_types,
            allowed_sources=context.allowed_sources,
        )
        reranked = rerank(safe_q, raw_docs, top_k=settings.max_reranked_documents)
        context_block, selected_docs = build_context(reranked)

        trace.span(
            name="retrieval",
            input={"query": safe_q, "source_types": source_types},
            output={"retrieved": len(raw_docs), "reranked": len(reranked), "context_docs": len(selected_docs)},
        )

        # ── Step 2: Crew assembly (adaptive complexity) ──────────────────────
        if workflow == "SEARCH" or len(selected_docs) == 0:
            result_text = await _run_simple_crew(safe_q, context_block, selected_docs)
        else:
            result_text = await _run_full_crew(safe_q, context_block, selected_docs, workflow)

        trace.span(name="generation", input={"workflow": workflow}, output={"answer_length": len(result_text)})

        # ── Step 3: Build structured response ────────────────────────────────
        latency_ms = int((time.monotonic() - start) * 1000)
        response = _build_response(
            question=safe_q,
            result_text=result_text,
            selected_docs=selected_docs,
            workflow=workflow,
            run_id=run_id,
            latency_ms=latency_ms,
        )
        trace.score("confidence", response["confidence"])
        return response


async def _run_simple_crew(question: str, context_block: str, docs: list[dict]) -> str:
    # Retrieval is already done at the flow level — the analyst works directly
    # on the pre-retrieved context_block, no tool calls needed.
    analyst = build_analyst()

    task = Task(
        description=(
            f"Synthesise an answer to: {question!r}\n\n"
            f"The following passages were retrieved from the enterprise knowledge base:\n\n"
            f"{context_block}\n\n"
            "Cite every claim with its doc_id. Report any conflicts between sources explicitly."
        ),
        expected_output="A structured answer with cited claims and source references.",
        agent=analyst,
    )

    crew = Crew(agents=[analyst], tasks=[task], process=Process.sequential, verbose=False)
    result = await crew.kickoff_async()
    return str(result)


async def _run_full_crew(question: str, context_block: str, docs: list[dict], workflow: str) -> str:
    # Retrieval is already done at the flow level. The crew plans, synthesises,
    # and verifies — all from the pre-retrieved context_block, no tool calls needed.
    planner = build_planner()
    analyst = build_analyst()
    verifier = build_verifier()

    t_plan = Task(
        description=(
            f"Break this question into 3–5 analysis sub-tasks: {question!r}\n\n"
            f"The following passages are available:\n\n{context_block}\n\n"
            "List which sub-questions each passage group can answer."
        ),
        expected_output="Numbered list of analysis sub-tasks mapped to available passages.",
        agent=planner,
    )
    t_analyse = Task(
        description=(
            f"Synthesise the retrieved evidence into a structured answer to: {question!r}\n\n"
            f"Context:\n{context_block}\n\n"
            "Produce: summary, claims with doc_ids, any conflicts, confidence score."
        ),
        expected_output="Structured answer: summary, cited claims, conflicts, confidence score.",
        agent=analyst,
    )
    t_verify = Task(
        description=(
            "Verify the analyst's answer. Check every claim has a doc_id from the retrieved evidence. "
            "Flag any claim without grounding. Confirm all parts of the question were answered."
        ),
        expected_output="Verification report: grounded claims, any ungrounded claims, final confidence.",
        agent=verifier,
    )

    crew = Crew(
        agents=[planner, analyst, verifier],
        tasks=[t_plan, t_analyse, t_verify],
        process=Process.sequential,
        verbose=False,
    )
    result = await crew.kickoff_async()
    return str(result)


def _build_response(
    question: str,
    result_text: str,
    selected_docs: list[dict],
    workflow: str,
    run_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    sources = [
        {
            "doc_id": d["doc_id"],
            "title": d["title"],
            "source_type": d["source_type"],
            "relevance_score": round(d.get("rerank_score", d.get("rrf_score", 0.0)), 4),
        }
        for d in selected_docs
    ]
    conflicts = _detect_conflicts(result_text)
    info_not_found = not selected_docs or "not found" in result_text.lower()
    confidence = 0.85 if selected_docs and not conflicts else (0.5 if conflicts else 0.1)

    return {
        "run_id": run_id,
        "topic": question[:100],
        "workflow": workflow,
        "summary": result_text,
        "sources": sources,
        "conflicts": conflicts,
        "information_not_found": info_not_found,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "tools_used": ["hybrid_search", "reranker"],
    }


def _detect_conflicts(text: str) -> list[str]:
    conflict_keywords = ["conflict", "contradict", "discrepancy", "disagree", "different version", "inconsistent"]
    if any(k in text.lower() for k in conflict_keywords):
        return ["Potential conflict detected in retrieved documents — review sources carefully."]
    return []
