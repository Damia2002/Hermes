"""Shared API request/response schemas."""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    user_id: str = "demo-user"
    session_id: str = "demo-session"
    question: str = Field(min_length=3, max_length=2_000)
    source_types: list[str] = Field(default_factory=list)
    response_mode: str = "detailed"


class QueryResponse(BaseModel):
    run_id: str
    topic: str
    workflow: str
    summary: str
    sources: list[dict]
    conflicts: list[str]
    information_not_found: bool
    confidence: float
    latency_ms: int
    tools_used: list[str]


class MonitorCreate(BaseModel):
    user_id: str = "demo-user"
    name: str = Field(min_length=3, max_length=100)
    query: str = Field(min_length=5, max_length=2_000)
    source_types: list[str] = Field(default_factory=list)
    schedule_cron: str = "0 * * * *"


class ActionApprove(BaseModel):
    user_id: str = "demo-user"
    decision: str = Field(pattern="^(approve|reject)$")
    note: str | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
