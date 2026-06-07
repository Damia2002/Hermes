"""Local embedding model using sentence-transformers with MPS/CPU fallback."""

from functools import lru_cache
from typing import Sequence

from app.config import get_settings
from app.observability.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    import torch
    from sentence_transformers import SentenceTransformer

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info("loading_embedding_model", model=settings.embedding_model, device=device)
    model = SentenceTransformer(settings.embedding_model, device=device)
    logger.info("embedding_model_ready", model=settings.embedding_model)
    return model


def embed_texts(texts: Sequence[str], batch_size: int | None = None) -> list[list[float]]:
    """Embed a list of texts. Returns a list of float vectors."""
    model = _load_model()
    effective_batch = batch_size or settings.embedding_batch_size
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), effective_batch):
        batch = texts[i : i + effective_batch]
        vecs = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        all_embeddings.extend(vecs.tolist())
    return all_embeddings


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]


def get_embedding_dimension() -> int:
    model = _load_model()
    return model.get_sentence_embedding_dimension()
