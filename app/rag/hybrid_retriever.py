"""Hybrid retrieval: dense (Qdrant) + sparse (SQLite FTS5) fused via RRF."""

import sqlite3
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.config import get_settings
from app.observability.logging import get_logger
from app.rag.embeddings import embed_query
from app.rag.ingestion import SPARSE_DB_PATH

settings = get_settings()
logger = get_logger(__name__)


def _get_qdrant() -> QdrantClient:
    return QdrantClient(path=settings.qdrant_path)


def _qdrant_filter(source_types: list[str] | None, allowed_sources: list[str] | None) -> Filter | None:
    sources = source_types or []
    if allowed_sources and "*" not in allowed_sources:
        sources = [s for s in sources if s in allowed_sources] if sources else list(allowed_sources)
    if not sources:
        return None
    return Filter(must=[FieldCondition(key="source_type", match=MatchAny(any=sources))])


def _dense_search(query: str, top_k: int, source_types: list[str] | None, allowed_sources: list[str] | None) -> list[dict]:
    qdrant = _get_qdrant()
    vector = embed_query(query)
    filt = _qdrant_filter(source_types, allowed_sources)
    response = qdrant.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=top_k,
        query_filter=filt,
        with_payload=True,
    )
    return [
        {
            "chunk_id": r.payload.get("chunk_id", ""),
            "doc_id": r.payload.get("doc_id", ""),
            "source_type": r.payload.get("source_type", ""),
            "title": r.payload.get("title", ""),
            "content": r.payload.get("content", ""),
            "score": r.score,
            "retrieval_type": "dense",
        }
        for r in response.points
    ]


def _sparse_search(query: str, top_k: int, source_types: list[str] | None, allowed_sources: list[str] | None) -> list[dict]:
    if not Path(SPARSE_DB_PATH).exists():
        logger.warning("sparse_db_not_found", path=SPARSE_DB_PATH)
        return []

    conn = sqlite3.connect(SPARSE_DB_PATH)
    conn.row_factory = sqlite3.Row

    source_filter = ""
    params: list = [query, top_k]
    sources = source_types or []
    if allowed_sources and "*" not in allowed_sources:
        sources = [s for s in sources if s in allowed_sources] if sources else list(allowed_sources)
    if sources:
        placeholders = ",".join("?" * len(sources))
        source_filter = f"AND m.source_type IN ({placeholders})"
        params = [query] + sources + [top_k]

    sql = f"""
        SELECT f.chunk_id, f.doc_id, f.source_type, f.title, f.content,
               bm25(chunks_fts) AS score
        FROM chunks_fts f
        JOIN chunks_meta m ON f.chunk_id = m.chunk_id
        WHERE chunks_fts MATCH ?
        {source_filter}
        ORDER BY score
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()

    return [
        {
            "chunk_id": row["chunk_id"],
            "doc_id": row["doc_id"],
            "source_type": row["source_type"],
            "title": row["title"],
            "content": row["content"],
            "score": abs(row["score"]),
            "retrieval_type": "sparse",
        }
        for row in rows
    ]


def _reciprocal_rank_fusion(ranked_lists: list[list[dict]], k: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            docs[cid] = doc

    fused = sorted(docs.values(), key=lambda d: scores[d["chunk_id"]], reverse=True)
    for doc in fused:
        doc["rrf_score"] = scores[doc["chunk_id"]]
    return fused


def hybrid_search(
    query: str,
    top_k: int | None = None,
    source_types: list[str] | None = None,
    allowed_sources: list[str] | None = None,
) -> list[dict]:
    """Run dense + sparse search and fuse with RRF."""
    n = top_k or settings.max_retrieved_documents

    dense = _dense_search(query, n, source_types, allowed_sources)
    sparse = _sparse_search(query, n, source_types, allowed_sources)

    fused = _reciprocal_rank_fusion([dense, sparse])

    # Deduplicate by doc_id (keep highest rrf_score per doc)
    seen_docs: dict[str, dict] = {}
    for doc in fused:
        did = doc["doc_id"]
        if did not in seen_docs or doc["rrf_score"] > seen_docs[did]["rrf_score"]:
            seen_docs[did] = doc

    results = sorted(seen_docs.values(), key=lambda d: d["rrf_score"], reverse=True)[:n]
    logger.info("hybrid_search", query_snippet=query[:60], dense=len(dense), sparse=len(sparse), fused=len(results))
    return results
