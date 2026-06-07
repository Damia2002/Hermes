"""Streaming document ingestion pipeline: chunk → embed → persist."""

import asyncio
import sqlite3
from pathlib import Path
from typing import Iterator

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import get_settings
from app.observability.logging import get_logger
from app.rag.chunking import Chunk, chunk_document
from app.rag.embeddings import embed_texts, get_embedding_dimension

settings = get_settings()
logger = get_logger(__name__)

SPARSE_DB_PATH = "./storage/bm25.db"


def _get_qdrant() -> QdrantClient:
    Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=settings.qdrant_path)


def _ensure_qdrant_collection(client: QdrantClient, dim: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info("qdrant_collection_created", name=settings.qdrant_collection, dim=dim)


def _get_sparse_db() -> sqlite3.Connection:
    Path(SPARSE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SPARSE_DB_PATH)
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(
            chunk_id UNINDEXED,
            doc_id UNINDEXED,
            source_type UNINDEXED,
            title,
            content,
            tokenize='porter unicode61'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks_meta (
            chunk_id TEXT PRIMARY KEY,
            doc_id   TEXT,
            source_type TEXT,
            title    TEXT,
            author   TEXT,
            timestamp TEXT,
            access_scope TEXT
        )
        """
    )
    conn.commit()
    return conn


def _batch(iterable, size: int) -> Iterator:
    buf: list = []
    for item in iterable:
        buf.append(item)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def ingest_documents(
    documents: list[dict],
    resume_from: int = 0,
    progress_callback=None,
) -> dict:
    """Main ingestion entry point.

    Streams documents → chunks → embeddings → Qdrant + SQLite FTS.
    Supports resumption via resume_from (chunk index).
    """
    qdrant = _get_qdrant()
    dim = get_embedding_dimension()
    _ensure_qdrant_collection(qdrant, dim)
    sparse_db = _get_sparse_db()

    total_chunks = 0
    skipped = 0
    embed_batch: int = settings.embedding_batch_size
    write_batch: int = settings.index_write_batch_size

    chunk_buffer: list[Chunk] = []
    chunk_index = 0

    for doc in documents:
        chunks = chunk_document(doc)
        for chunk in chunks:
            if chunk_index < resume_from:
                chunk_index += 1
                skipped += 1
                continue
            chunk_buffer.append(chunk)
            chunk_index += 1

            if len(chunk_buffer) >= write_batch:
                _flush(chunk_buffer, qdrant, sparse_db, embed_batch)
                total_chunks += len(chunk_buffer)
                if progress_callback:
                    progress_callback(total_chunks)
                chunk_buffer = []

    if chunk_buffer:
        _flush(chunk_buffer, qdrant, sparse_db, embed_batch)
        total_chunks += len(chunk_buffer)

    sparse_db.close()
    logger.info("ingestion_complete", total_chunks=total_chunks, skipped=skipped)
    return {"total_chunks": total_chunks, "skipped": skipped}


def _flush(chunks: list[Chunk], qdrant: QdrantClient, sparse_db: sqlite3.Connection, embed_batch: int) -> None:
    texts = [f"{c.title}\n{c.content}" for c in chunks]
    vectors = embed_texts(texts, batch_size=embed_batch)

    points = [
        PointStruct(
            id=abs(hash(c.chunk_id)) % (10**15),
            vector=vec,
            payload={
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "source_type": c.source_type,
                "title": c.title,
                "content": c.content,
                "section": c.section,
                "author": c.author,
                "timestamp": c.timestamp,
                "access_scope": c.access_scope,
                "parent_document": c.parent_document,
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    qdrant.upsert(collection_name=settings.qdrant_collection, points=points)

    rows_fts = [(c.chunk_id, c.doc_id, c.source_type, c.title, c.content) for c in chunks]
    rows_meta = [(c.chunk_id, c.doc_id, c.source_type, c.title, c.author, c.timestamp, c.access_scope) for c in chunks]
    sparse_db.executemany("INSERT OR REPLACE INTO chunks_fts VALUES (?,?,?,?,?)", rows_fts)
    sparse_db.executemany("INSERT OR REPLACE INTO chunks_meta VALUES (?,?,?,?,?,?,?)", rows_meta)
    sparse_db.commit()
