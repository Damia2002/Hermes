"""Base tool infrastructure: typed contracts, execution context, error types."""

import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.observability.logging import get_logger
from app.safety.permissions import ExecutionContext

logger = get_logger(__name__)


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: ToolError | None = None


class BaseTool(ABC):
    """All HERMES tools extend this class."""

    name: str = "base_tool"
    description: str = ""
    requires_approval: bool = False

    def run(self, input: BaseModel, context: ExecutionContext) -> ToolResult:
        start = time.monotonic()
        try:
            result = self._execute(input, context)
            latency = int((time.monotonic() - start) * 1000)
            logger.info("tool_success", tool=self.name, user=context.user_id, latency_ms=latency)
            return ToolResult(success=True, data=result)
        except PermissionError as exc:
            logger.warning("tool_permission_denied", tool=self.name, error=str(exc))
            return ToolResult(
                success=False,
                error=ToolError(code="permission_denied", message=str(exc), retryable=False),
            )
        except ValueError as exc:
            logger.warning("tool_validation_error", tool=self.name, error=str(exc))
            return ToolResult(
                success=False,
                error=ToolError(code="validation_error", message=str(exc), retryable=False),
            )
        except Exception as exc:
            logger.error("tool_error", tool=self.name, error=str(exc))
            return ToolResult(
                success=False,
                error=ToolError(code="internal_error", message=str(exc), retryable=True),
            )

    @abstractmethod
    def _execute(self, input: BaseModel, context: ExecutionContext) -> Any:
        ...
