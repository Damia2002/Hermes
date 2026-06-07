"""Reliability tests: retry logic, timeouts, fallback behaviour."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


TRANSIENT_HTTP_CODES = {429, 502, 503}
NON_RETRYABLE_HTTP_CODES = {400, 401, 403, 404, 422}


class TransientError(Exception):
    """Simulates a transient network/API error."""


class PermanentError(Exception):
    """Simulates a non-retryable error (e.g., bad input)."""


class FakeRetryer:
    def __init__(self, fail_n_times: int):
        self.attempts = 0
        self.fail_n = fail_n_times

    @retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.01, min=0.01, max=0.1),
    )
    def call(self) -> str:
        self.attempts += 1
        if self.attempts <= self.fail_n:
            raise TransientError("rate limit")
        return "success"


def test_retry_succeeds_after_transient_failures():
    r = FakeRetryer(fail_n_times=2)
    result = r.call()
    assert result == "success"
    assert r.attempts == 3


def test_retry_exhausted_raises():
    r = FakeRetryer(fail_n_times=10)
    with pytest.raises(Exception):
        r.call()


def test_permanent_error_not_retried():
    class NeverRetrier:
        attempts = 0

        @retry(
            retry=retry_if_exception_type(TransientError),
            stop=stop_after_attempt(3),
        )
        def call(self):
            self.attempts += 1
            raise PermanentError("bad input")

    nr = NeverRetrier()
    with pytest.raises(PermanentError):
        nr.call()
    assert nr.attempts == 1


@pytest.mark.asyncio
async def test_retrieval_timeout_fallback():
    """Reranker failure should fall back to hybrid order."""
    from unittest.mock import patch

    docs = [
        {"chunk_id": "c1", "doc_id": "d1", "title": "T", "source_type": "confluence", "content": "text", "rrf_score": 0.9},
        {"chunk_id": "c2", "doc_id": "d2", "title": "T2", "source_type": "jira", "content": "text2", "rrf_score": 0.7},
    ]

    with patch("app.rag.reranker._load_reranker", side_effect=RuntimeError("reranker unavailable")):
        from app.rag.reranker import rerank
        result = rerank("test query", docs, top_k=2)

    assert len(result) == 2
    assert result[0]["doc_id"] == "d1"


def test_tool_error_is_retryable():
    from app.tools.base import ToolError
    err = ToolError(code="internal_error", message="timeout", retryable=True)
    assert err.retryable is True


def test_validation_error_not_retryable():
    from app.tools.base import ToolError
    err = ToolError(code="validation_error", message="bad input", retryable=False)
    assert err.retryable is False
