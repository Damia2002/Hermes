"""Cross-encoder reranking with MPS/CPU fallback."""

from functools import lru_cache

from app.config import get_settings
from app.observability.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_reranker():
    import torch
    from sentence_transformers import CrossEncoder

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info("loading_reranker", model=settings.reranker_model, device=device)
    model = CrossEncoder(settings.reranker_model, device=device)
    logger.info("reranker_ready", model=settings.reranker_model)
    return model


def rerank(query: str, documents: list[dict], top_k: int | None = None) -> list[dict]:
    """Rerank documents by cross-encoder relevance to query.

    Falls back to original order if the reranker fails (reliability requirement).
    """
    if not documents:
        return documents

    n = top_k or settings.max_reranked_documents

    try:
        model = _load_reranker()
        pairs = [(query, doc["content"]) for doc in documents]
        scores = model.predict(pairs)
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        result = []
        for doc, score in ranked[:n]:
            doc = dict(doc)
            doc["rerank_score"] = float(score)
            result.append(doc)
        logger.info("reranking_complete", input=len(documents), output=len(result))
        return result
    except Exception as exc:
        logger.warning("reranker_failed", error=str(exc), fallback="returning_hybrid_order")
        return documents[:n]
