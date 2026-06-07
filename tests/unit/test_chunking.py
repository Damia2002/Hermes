"""Unit tests: source-aware chunking."""

import pytest
from app.rag.chunking import chunk_document, Chunk


def make_doc(source_type: str, content: str) -> dict:
    return {
        "doc_id": "test-doc-1",
        "source_type": source_type,
        "title": "Test Document",
        "content": content,
        "author": "tester",
        "timestamp": "2024-01-01",
        "access_scope": "internal",
    }


def test_confluence_heading_chunks():
    doc = make_doc("confluence", "# Introduction\nThis is intro.\n# Method\nThis is method.")
    chunks = chunk_document(doc)
    assert len(chunks) >= 1
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.doc_id == "test-doc-1" for c in chunks)


def test_jira_single_chunk():
    doc = make_doc("jira", "Issue summary. Priority: high. Status: open.")
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].source_type == "jira"


def test_slack_thread_chunks():
    messages = "Hello world\n---\nYes, agreed\n---\nThanks everyone"
    doc = make_doc("slack", messages)
    chunks = chunk_document(doc)
    assert len(chunks) >= 1


def test_fixed_chunking_preserves_content():
    long_content = " ".join(["word"] * 600)
    doc = make_doc("github", long_content)
    chunks = chunk_document(doc)
    reconstructed = " ".join(c.content for c in chunks)
    assert "word" in reconstructed
    assert len(chunks) > 1


def test_chunk_ids_are_unique():
    doc = make_doc("confluence", " ".join(["text"] * 800))
    chunks = chunk_document(doc)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
