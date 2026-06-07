"""Retrieval agent: rewrites queries, runs hybrid search, deduplicates, reranks."""

from crewai import Agent
from crewai.tools import tool

from app.agents.llm_factory import get_fast_llm
from app.config import get_settings
from app.rag.hybrid_retriever import hybrid_search
from app.rag.reranker import rerank

settings = get_settings()


@tool("hybrid_knowledge_search")
def hybrid_knowledge_search(query: str, source_types: str = "") -> str:
    """Search enterprise knowledge base with hybrid retrieval.
    source_types: comma-separated list (e.g. 'confluence,jira').
    Returns top passages with doc_id, title, source, content.
    """
    sources = [s.strip() for s in source_types.split(",") if s.strip()] or None
    docs = hybrid_search(query=query, top_k=settings.max_retrieved_documents, source_types=sources)
    docs = rerank(query, docs, top_k=settings.max_reranked_documents)
    if not docs:
        return "No relevant documents found."
    parts = []
    for d in docs[: settings.max_llm_context_documents]:
        parts.append(
            f"[doc_id={d['doc_id']} source={d['source_type']} title={d['title']!r}]\n{d['content'][:600]}"
        )
    return "\n\n---\n\n".join(parts)


def build_retriever() -> Agent:
    return Agent(
        role="Retrieval Specialist",
        goal=(
            "Retrieve the most relevant enterprise documents for a given question or sub-question. "
            "Rewrite the query if needed, run hybrid search, and return a ranked list of passages "
            "with their doc_ids and source types."
        ),
        backstory=(
            "You are an expert at enterprise information retrieval. "
            "You know that enterprise questions often use internal jargon, "
            "so you paraphrase queries to improve recall. "
            "You always cite the doc_id for every passage you return."
        ),
        llm=get_fast_llm(),
        tools=[hybrid_knowledge_search],
        verbose=True,
        allow_delegation=False,
        max_iter=settings.max_agent_iterations,
    )
