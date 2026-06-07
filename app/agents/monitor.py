"""Monitor agent: compares snapshots and classifies information changes."""

from crewai import Agent
from crewai.tools import tool

from app.agents.llm_factory import get_primary_llm
from app.config import get_settings
from app.rag.hybrid_retriever import hybrid_search

settings = get_settings()


@tool("compare_knowledge_snapshots")
def compare_knowledge_snapshots(query: str, previous_doc_ids: str) -> str:
    """Compare current retrieval results for a query against a previous snapshot.
    previous_doc_ids: comma-separated list of doc_ids from the prior run.
    Returns change classification and summary.
    """
    prev_ids = set(d.strip() for d in previous_doc_ids.split(",") if d.strip())
    current_docs = hybrid_search(query=query, top_k=settings.max_retrieved_documents)
    current_ids = {d["doc_id"] for d in current_docs}

    new_ids = current_ids - prev_ids
    removed_ids = prev_ids - current_ids

    if new_ids and removed_ids:
        change_type = "CHANGED_INFORMATION"
    elif new_ids:
        change_type = "NEW_INFORMATION"
    elif removed_ids:
        change_type = "DOCUMENT_REMOVED"
    else:
        change_type = "NO_MATERIAL_CHANGE"

    return (
        f"Change type: {change_type}\n"
        f"New document IDs ({len(new_ids)}): {', '.join(list(new_ids)[:5])}\n"
        f"Removed IDs ({len(removed_ids)}): {', '.join(list(removed_ids)[:5])}"
    )


def build_monitor() -> Agent:
    return Agent(
        role="Change Monitor",
        goal=(
            "Run a saved monitoring query, compare current retrieval results to the previous snapshot, "
            "classify the change (NEW_INFORMATION / CHANGED_INFORMATION / DOCUMENT_REMOVED / NO_MATERIAL_CHANGE), "
            "and produce a concise change report. Only generate an alert when the change is material."
        ),
        backstory=(
            "You are responsible for watching enterprise knowledge over time. "
            "You know what was retrieved last time and you compare it with current results. "
            "You write clear, specific change reports — never vague alerts."
        ),
        llm=get_primary_llm(),
        tools=[compare_knowledge_snapshots],
        verbose=True,
        allow_delegation=False,
        max_iter=settings.max_agent_iterations,
    )
