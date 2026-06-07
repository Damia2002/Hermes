"""Knowledge retrieval tools: search and document fetch."""

from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.context_builder import build_context
from app.rag.hybrid_retriever import hybrid_search
from app.rag.reranker import rerank
from app.safety.injection import validate_user_input
from app.safety.permissions import ExecutionContext
from app.tools.base import BaseTool

settings = get_settings()


class KnowledgeSearchInput(BaseModel):
    query: str = Field(min_length=3, max_length=2_000)
    user_id: str
    source_types: list[str] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=50)
    rerank_results: bool = True


class RetrievedDocument(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    source_type: str
    content: str
    retrieval_score: float


class KnowledgeSearchOutput(BaseModel):
    documents: list[RetrievedDocument]
    query_used: str
    retrieval_strategy: str


class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge"
    description = "Search the enterprise knowledge base using hybrid dense + sparse retrieval."

    def _execute(self, input: KnowledgeSearchInput, context: ExecutionContext) -> KnowledgeSearchOutput:
        safe_query = validate_user_input(input.query)

        source_types = [s for s in input.source_types if context.can_read_source(s)] if input.source_types else None

        raw = hybrid_search(
            query=safe_query,
            top_k=settings.max_retrieved_documents,
            source_types=source_types,
            allowed_sources=context.allowed_sources,
        )

        if input.rerank_results:
            raw = rerank(safe_query, raw, top_k=settings.max_reranked_documents)

        docs = [
            RetrievedDocument(
                doc_id=d["doc_id"],
                chunk_id=d["chunk_id"],
                title=d["title"],
                source_type=d["source_type"],
                content=d["content"],
                retrieval_score=d.get("rerank_score", d.get("rrf_score", 0.0)),
            )
            for d in raw[: input.top_k]
        ]

        strategy = "hybrid+rerank" if input.rerank_results else "hybrid"
        return KnowledgeSearchOutput(documents=docs, query_used=safe_query, retrieval_strategy=strategy)


class RetrieveDocumentInput(BaseModel):
    doc_id: str
    user_id: str


class RetrieveDocumentOutput(BaseModel):
    doc_id: str
    chunks: list[RetrievedDocument]
    context_block: str


class RetrieveDocumentTool(BaseTool):
    name = "retrieve_document"
    description = "Fetch all chunks for a known document ID and build a safe context block."

    def _execute(self, input: RetrieveDocumentInput, context: ExecutionContext) -> RetrieveDocumentOutput:
        # Use the sparse DB for doc-level fetch
        import sqlite3
        from pathlib import Path
        from app.rag.ingestion import SPARSE_DB_PATH

        if not Path(SPARSE_DB_PATH).exists():
            return RetrieveDocumentOutput(doc_id=input.doc_id, chunks=[], context_block="")

        conn = sqlite3.connect(SPARSE_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT f.chunk_id, f.doc_id, f.source_type, f.title, f.content FROM chunks_fts f "
            "JOIN chunks_meta m ON f.chunk_id = m.chunk_id WHERE m.doc_id = ?",
            (input.doc_id,),
        ).fetchall()
        conn.close()

        raw = [
            {
                "doc_id": r["doc_id"],
                "chunk_id": r["chunk_id"],
                "source_type": r["source_type"],
                "title": r["title"],
                "content": r["content"],
                "rrf_score": 1.0,
            }
            for r in rows
        ]
        context.assert_can_read(raw[0]["source_type"] if raw else "unknown")
        context_block, selected = build_context(raw)

        chunks = [
            RetrievedDocument(
                doc_id=d["doc_id"],
                chunk_id=d["chunk_id"],
                title=d["title"],
                source_type=d["source_type"],
                content=d["content"],
                retrieval_score=1.0,
            )
            for d in selected
        ]
        return RetrieveDocumentOutput(doc_id=input.doc_id, chunks=chunks, context_block=context_block)


class CompareSnapshotsInput(BaseModel):
    query: str
    previous_doc_ids: list[str]
    user_id: str
    source_types: list[str] = Field(default_factory=list)


class CompareSnapshotsOutput(BaseModel):
    change_type: str
    new_doc_ids: list[str]
    removed_doc_ids: list[str]
    summary: str


class CompareSnapshotsTool(BaseTool):
    name = "compare_snapshots"
    description = "Compare current retrieval results against a previous snapshot to detect changes."

    def _execute(self, input: CompareSnapshotsInput, context: ExecutionContext) -> CompareSnapshotsOutput:
        current_docs = hybrid_search(
            query=input.query,
            top_k=settings.max_retrieved_documents,
            source_types=input.source_types or None,
            allowed_sources=context.allowed_sources,
        )
        current_ids = {d["doc_id"] for d in current_docs}
        previous_ids = set(input.previous_doc_ids)

        new_ids = list(current_ids - previous_ids)
        removed_ids = list(previous_ids - current_ids)

        if new_ids and removed_ids:
            change_type = "CHANGED_INFORMATION"
        elif new_ids:
            change_type = "NEW_INFORMATION"
        elif removed_ids:
            change_type = "DOCUMENT_REMOVED"
        else:
            change_type = "NO_MATERIAL_CHANGE"

        summary = (
            f"Change type: {change_type}. "
            f"New documents: {len(new_ids)}. Removed: {len(removed_ids)}."
        )
        return CompareSnapshotsOutput(
            change_type=change_type,
            new_doc_ids=new_ids,
            removed_doc_ids=removed_ids,
            summary=summary,
        )
