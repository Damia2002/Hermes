"""Monitor management tools: save, list, delete monitoring rules."""

from pydantic import BaseModel, Field

from app.safety.permissions import ExecutionContext
from app.tools.base import BaseTool


class SaveMonitorInput(BaseModel):
    user_id: str
    name: str = Field(min_length=3, max_length=100)
    query: str = Field(min_length=5, max_length=2_000)
    source_types: list[str] = Field(default_factory=list)
    schedule_cron: str = "0 * * * *"


class MonitorSaved(BaseModel):
    monitor_id: str
    name: str
    query: str
    source_types: list[str]
    schedule_cron: str
    status: str = "saved"


class SaveMonitorTool(BaseTool):
    name = "save_monitor"
    description = "Save a monitoring rule that will be checked on a schedule."

    def _execute(self, input: SaveMonitorInput, context: ExecutionContext) -> MonitorSaved:
        context.assert_can_act("save_monitor")
        import uuid
        monitor_id = str(uuid.uuid4())
        return MonitorSaved(
            monitor_id=monitor_id,
            name=input.name,
            query=input.query,
            source_types=input.source_types,
            schedule_cron=input.schedule_cron,
        )


class WriteInternalNoteInput(BaseModel):
    user_id: str
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=5, max_length=20_000)
    tags: list[str] = Field(default_factory=list)


class InternalNote(BaseModel):
    note_id: str
    title: str
    content: str
    tags: list[str]
    status: str = "saved"


class WriteInternalNoteTool(BaseTool):
    name = "write_note"
    description = "Write an internal note to the HERMES memory system."

    def _execute(self, input: WriteInternalNoteInput, context: ExecutionContext) -> InternalNote:
        context.assert_can_act("write_note")
        import uuid
        note_id = str(uuid.uuid4())
        return InternalNote(
            note_id=note_id,
            title=input.title,
            content=input.content,
            tags=input.tags,
        )
