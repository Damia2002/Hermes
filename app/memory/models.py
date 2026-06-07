"""Memory entry schemas."""

from pydantic import BaseModel, Field


class MemoryEntryCreate(BaseModel):
    user_id: str
    content: str = Field(min_length=3, max_length=10_000)
    memory_type: str = "episodic"
    tags: list[str] = Field(default_factory=list)


class MemoryEntryRead(BaseModel):
    id: str
    user_id: str
    content: str
    memory_type: str
    tags: list[str]
    created_at: str

    class Config:
        from_attributes = True
