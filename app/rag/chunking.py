"""Source-aware document chunking strategies."""

from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings

settings = get_settings()


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source_type: str
    title: str
    content: str
    section: str = ""
    author: str = ""
    timestamp: str = ""
    access_scope: str = "internal"
    parent_document: str = ""
    metadata: dict = field(default_factory=dict)


def _split_by_tokens(text: str, max_tokens: int, overlap: int) -> list[str]:
    """Naive word-based chunking; tiktoken is used in build_index for accuracy."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


SOURCE_STRATEGIES = {
    "confluence":  "heading",
    "google_drive": "heading",
    "slack":       "thread",
    "gmail":       "email_thread",
    "jira":        "issue",
    "linear":      "issue",
    "github":      "pr",
    "fireflies":   "speaker",
    "hubspot":     "record",
}


def chunk_document(doc: dict[str, Any]) -> list[Chunk]:
    source_type = doc.get("source_type", "unknown")
    strategy = SOURCE_STRATEGIES.get(source_type, "fixed")

    doc_id = doc.get("doc_id", "")
    title = doc.get("title", "Untitled")
    content = doc.get("content", "")
    author = doc.get("author", "")
    timestamp = doc.get("timestamp", "")
    access_scope = doc.get("access_scope", "internal")
    max_tok = settings.max_chunk_tokens
    overlap = settings.chunk_overlap_tokens

    if strategy == "heading":
        return _heading_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap)
    if strategy in ("issue", "record"):
        return _single_chunk(doc_id, source_type, title, content, author, timestamp, access_scope)
    if strategy == "thread":
        return _thread_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap)
    return _fixed_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap)


def _single_chunk(doc_id, source_type, title, content, author, timestamp, access_scope) -> list[Chunk]:
    return [
        Chunk(
            chunk_id=f"{doc_id}_0",
            doc_id=doc_id,
            source_type=source_type,
            title=title,
            content=content[:4000],
            author=author,
            timestamp=timestamp,
            access_scope=access_scope,
            parent_document=doc_id,
        )
    ]


def _fixed_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap) -> list[Chunk]:
    parts = _split_by_tokens(content, max_tok, overlap)
    return [
        Chunk(
            chunk_id=f"{doc_id}_{i}",
            doc_id=doc_id,
            source_type=source_type,
            title=title,
            content=part,
            author=author,
            timestamp=timestamp,
            access_scope=access_scope,
            parent_document=doc_id,
        )
        for i, part in enumerate(parts)
    ]


def _heading_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap) -> list[Chunk]:
    import re
    sections = re.split(r"\n#{1,4} ", content)
    chunks: list[Chunk] = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        lines = section.split("\n", 1)
        section_title = lines[0].strip() if lines else ""
        section_body = lines[1] if len(lines) > 1 else section
        for j, part in enumerate(_split_by_tokens(section_body, max_tok, overlap)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}_{i}_{j}",
                    doc_id=doc_id,
                    source_type=source_type,
                    title=f"{title} › {section_title}",
                    content=part,
                    section=section_title,
                    author=author,
                    timestamp=timestamp,
                    access_scope=access_scope,
                    parent_document=doc_id,
                )
            )
    return chunks or _fixed_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap)


def _thread_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap) -> list[Chunk]:
    messages = content.split("\n---\n")
    chunks: list[Chunk] = []
    for i, msg in enumerate(messages):
        msg = msg.strip()
        if not msg:
            continue
        for j, part in enumerate(_split_by_tokens(msg, max_tok, overlap)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}_{i}_{j}",
                    doc_id=doc_id,
                    source_type=source_type,
                    title=title,
                    content=part,
                    author=author,
                    timestamp=timestamp,
                    access_scope=access_scope,
                    parent_document=doc_id,
                )
            )
    return chunks or _fixed_chunks(doc_id, source_type, title, content, author, timestamp, access_scope, max_tok, overlap)
