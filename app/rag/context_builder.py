"""Build a safe, token-bounded context from reranked documents."""

from app.config import get_settings
from app.safety.injection import build_safe_context

settings = get_settings()

MAX_CONTEXT_CHARS = settings.max_llm_context_documents * settings.max_chunk_tokens * 5


def build_context(documents: list[dict], max_docs: int | None = None) -> tuple[str, list[dict]]:
    """Select top documents, wrap them in injection-safe delimiters, return context + selected docs."""
    n = max_docs or settings.max_llm_context_documents
    selected = documents[:n]
    context = build_safe_context(selected)
    return context, selected
