"""Langfuse v4 tracing with local JSON fallback."""

import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from app.config import get_settings
from app.observability.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_langfuse_client: Any = None


def _init_langfuse() -> Any:
    if not settings.langfuse_enabled:
        return None
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("langfuse_disabled", reason="missing keys")
        return None
    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        client.auth_check()
        logger.info("langfuse_connected", host=settings.langfuse_host)
        return client
    except Exception as exc:
        logger.warning("langfuse_init_failed", error=str(exc))
        return None


def get_langfuse() -> Any:
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = _init_langfuse()
    return _langfuse_client


class LocalTraceWriter:
    def __init__(self, log_dir: str = settings.log_dir) -> None:
        self.path = Path(log_dir) / "traces.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, trace: dict) -> None:
        with self.path.open("a") as f:
            f.write(json.dumps(trace) + "\n")


_local_writer = LocalTraceWriter()


class HermesTrace:
    """Thin wrapper that records spans locally and optionally to Langfuse v4."""

    def __init__(self, name: str, user_id: str, metadata: dict | None = None) -> None:
        self.trace_id = str(uuid.uuid4())
        self.name = name
        self.user_id = user_id
        self.metadata = metadata or {}
        self.start_time = time.monotonic()
        self._spans: list[dict] = []
        self._lf = get_langfuse()
        self._lf_ctx = None

        if self._lf:
            try:
                # Langfuse v4.7: as_type replaces type; user_id goes in metadata
                self._lf_ctx = self._lf.start_as_current_observation(
                    name=name,
                    as_type="agent",
                    metadata={"user_id": user_id, **(metadata or {})},
                )
                self._lf_ctx.__enter__()
                self.trace_id = self._lf.get_current_trace_id() or self.trace_id
            except Exception as exc:
                logger.warning("langfuse_trace_start_failed", error=str(exc))
                self._lf_ctx = None

    def span(self, name: str, input: Any = None, output: Any = None, metadata: dict | None = None) -> None:
        self._spans.append({"name": name, "input": input, "output": output})
        if self._lf and self._lf_ctx:
            try:
                self._lf.create_event(name=name, input=input, output=output, metadata=metadata)
            except Exception:
                pass

    def generation(self, name: str, model: str, prompt: Any, completion: Any, usage: dict | None = None) -> None:
        self._spans.append({"name": name, "model": model, "prompt": prompt, "completion": completion})

    def score(self, name: str, value: float) -> None:
        if self._lf:
            try:
                self._lf.score_current_trace(name=name, value=value)
            except Exception:
                pass

    def end(self, status: str = "completed") -> None:
        elapsed_ms = int((time.monotonic() - self.start_time) * 1000)

        if self._lf_ctx:
            try:
                self._lf_ctx.__exit__(None, None, None)
                self._lf.flush()
            except Exception:
                pass

        _local_writer.write({
            "trace_id": self.trace_id,
            "name": self.name,
            "user_id": self.user_id,
            "status": status,
            "latency_ms": elapsed_ms,
            "metadata": self.metadata,
            "spans": self._spans,
        })
        logger.info(
            "trace_ended",
            trace_id=self.trace_id,
            workflow=self.name,
            status=status,
            latency_ms=elapsed_ms,
        )


@contextmanager
def trace_workflow(name: str, user_id: str, metadata: dict | None = None) -> Generator[HermesTrace, None, None]:
    t = HermesTrace(name=name, user_id=user_id, metadata=metadata)
    try:
        yield t
        t.end(status="completed")
    except Exception as exc:
        t.end(status="error")
        raise exc
