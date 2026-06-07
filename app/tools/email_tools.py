"""Mock email tools (draft creation only; no real credentials)."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

from app.safety.permissions import ExecutionContext
from app.tools.base import BaseTool


class EmailDraftInput(BaseModel):
    to: list[str] = Field(min_length=1)
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=20_000)
    cc: list[str] = Field(default_factory=list)
    supporting_doc_ids: list[str] = Field(default_factory=list)
    user_id: str


class EmailDraft(BaseModel):
    draft_id: str
    to: list[str]
    subject: str
    body: str
    cc: list[str]
    supporting_doc_ids: list[str]
    status: str = "draft"
    created_at: str


class CreateEmailDraftTool(BaseTool):
    name = "create_email_draft"
    description = "Prepare an email draft. Requires human approval before sending."
    requires_approval = True

    def _execute(self, input: EmailDraftInput, context: ExecutionContext) -> EmailDraft:
        context.assert_can_act("create_draft")
        draft_id = f"EMAIL-{str(uuid.uuid4())[:8]}"
        return EmailDraft(
            draft_id=draft_id,
            to=input.to,
            subject=input.subject,
            body=input.body,
            cc=input.cc,
            supporting_doc_ids=input.supporting_doc_ids,
            created_at=datetime.utcnow().isoformat(),
        )


class ReadEmailThreadInput(BaseModel):
    thread_id: str
    user_id: str


class EmailThread(BaseModel):
    thread_id: str
    subject: str
    participants: list[str]
    messages: list[dict]


class ReadEmailThreadTool(BaseTool):
    name = "read_email_thread"
    description = "Read an email thread by ID (mock demo data)."

    def _execute(self, input: ReadEmailThreadInput, context: ExecutionContext) -> EmailThread:
        context.assert_can_read("gmail")
        return EmailThread(
            thread_id=input.thread_id,
            subject=f"[MOCK] Thread {input.thread_id}",
            participants=["alice@rocket.internal", "bob@rocket.internal"],
            messages=[
                {
                    "from": "alice@rocket.internal",
                    "body": "This is a mock email message for the demo environment.",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
        )
