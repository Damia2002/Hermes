"""Mock Jira tools (same interface as real Jira, no credentials required for demo)."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from app.safety.permissions import ExecutionContext
from app.tools.base import BaseTool


class JiraTicketInput(BaseModel):
    summary: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)
    issue_type: str = "Task"
    priority: str = "Medium"
    labels: list[str] = Field(default_factory=list)
    supporting_doc_ids: list[str] = Field(default_factory=list)
    user_id: str


class JiraTicketDraft(BaseModel):
    draft_id: str
    summary: str
    description: str
    issue_type: str
    priority: str
    labels: list[str]
    supporting_doc_ids: list[str]
    status: str = "draft"
    created_at: str


class CreateJiraDraftTool(BaseTool):
    name = "create_jira_draft"
    description = "Create a draft Jira issue (requires human approval before submission)."
    requires_approval = True

    def _execute(self, input: JiraTicketInput, context: ExecutionContext) -> JiraTicketDraft:
        context.assert_can_act("create_draft")
        draft_id = f"DRAFT-{str(uuid.uuid4())[:8].upper()}"
        return JiraTicketDraft(
            draft_id=draft_id,
            summary=input.summary,
            description=input.description,
            issue_type=input.issue_type,
            priority=input.priority,
            labels=input.labels,
            supporting_doc_ids=input.supporting_doc_ids,
            created_at=datetime.utcnow().isoformat(),
        )


class ReadJiraTicketInput(BaseModel):
    ticket_id: str
    user_id: str


class JiraTicketDetail(BaseModel):
    ticket_id: str
    summary: str
    description: str
    status: str
    assignee: str
    reporter: str
    created_at: str
    comments: list[str]


class ReadJiraTicketTool(BaseTool):
    name = "read_jira_ticket"
    description = "Read a Jira ticket by ID (mock: returns simulated data)."

    def _execute(self, input: ReadJiraTicketInput, context: ExecutionContext) -> JiraTicketDetail:
        context.assert_can_read("jira")
        return JiraTicketDetail(
            ticket_id=input.ticket_id,
            summary=f"[MOCK] Summary for {input.ticket_id}",
            description="This is a mock Jira ticket returned by the demo environment.",
            status="Open",
            assignee="engineer@rocket.internal",
            reporter="pm@rocket.internal",
            created_at=datetime.utcnow().isoformat(),
            comments=["Mock comment: deployment scheduled for next sprint."],
        )
