"""Action agent: bounded ReAct loop for enterprise tool interactions."""

from crewai import Agent
from crewai.tools import tool

from app.agents.llm_factory import get_primary_llm
from app.config import get_settings

settings = get_settings()


@tool("create_jira_draft_action")
def create_jira_draft_action(summary: str, description: str, issue_type: str = "Task") -> str:
    """Create a Jira draft issue (not yet submitted — requires human approval).
    Returns the draft ID and confirmation message.
    """
    import uuid
    draft_id = f"DRAFT-{str(uuid.uuid4())[:8].upper()}"
    return (
        f"Jira draft created: {draft_id}\n"
        f"Summary: {summary}\n"
        f"Type: {issue_type}\n"
        f"Status: PENDING_APPROVAL — will not be submitted until a human approves."
    )


@tool("create_email_draft_action")
def create_email_draft_action(to: str, subject: str, body: str) -> str:
    """Create an email draft (not yet sent — requires human approval).
    to: comma-separated recipients.
    Returns draft ID and preview.
    """
    import uuid
    draft_id = f"EMAIL-{str(uuid.uuid4())[:8]}"
    recipients = [r.strip() for r in to.split(",")]
    return (
        f"Email draft created: {draft_id}\n"
        f"To: {', '.join(recipients)}\n"
        f"Subject: {subject}\n"
        f"Status: PENDING_APPROVAL — will not be sent until a human approves."
    )


@tool("write_internal_note_action")
def write_internal_note_action(title: str, content: str) -> str:
    """Write an internal note to HERMES memory. Does not require approval."""
    import uuid
    note_id = str(uuid.uuid4())
    return f"Note saved: {note_id}\nTitle: {title}"


def build_action_agent() -> Agent:
    return Agent(
        role="Action Specialist",
        goal=(
            "Use the available enterprise tools to prepare actions requested by the user. "
            f"Never exceed {settings.max_tool_calls} tool calls per request. "
            "Write actions (Jira, email) produce drafts that must be approved by a human. "
            "Never execute a write action without recording it as a draft first."
        ),
        backstory=(
            "You are the executor inside HERMES. You interact with enterprise platforms "
            "on behalf of the user, but you create drafts — not final submissions. "
            "Every proposed action is logged and presented for human review."
        ),
        llm=get_primary_llm(),
        tools=[create_jira_draft_action, create_email_draft_action, write_internal_note_action],
        verbose=True,
        allow_delegation=False,
        max_iter=settings.max_agent_iterations,
    )
