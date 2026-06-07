"""Permission boundaries: execution context and access control."""

from pydantic import BaseModel, Field


ROLE_PERMISSIONS: dict[str, dict] = {
    "viewer": {
        "allowed_sources": ["confluence", "github", "jira", "slack", "gmail", "drive", "hubspot", "fireflies", "linear"],
        "allowed_actions": [],
        "can_approve": False,
    },
    "analyst": {
        "allowed_sources": ["confluence", "github", "jira", "slack", "gmail", "drive", "hubspot", "fireflies", "linear"],
        "allowed_actions": ["create_draft", "save_monitor", "write_note"],
        "can_approve": False,
    },
    "admin": {
        "allowed_sources": ["*"],
        "allowed_actions": ["*"],
        "can_approve": True,
    },
}


class ExecutionContext(BaseModel):
    user_id: str
    session_id: str
    roles: list[str] = Field(default_factory=lambda: ["viewer"])
    allowed_sources: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    can_approve: bool = False

    @classmethod
    def from_roles(cls, user_id: str, session_id: str, roles: list[str]) -> "ExecutionContext":
        sources: set[str] = set()
        actions: set[str] = set()
        can_approve = False

        for role in roles:
            perms = ROLE_PERMISSIONS.get(role, {})
            if perms.get("allowed_sources") == ["*"]:
                sources = {"*"}
            else:
                sources.update(perms.get("allowed_sources", []))
            if perms.get("allowed_actions") == ["*"]:
                actions = {"*"}
            else:
                actions.update(perms.get("allowed_actions", []))
            if perms.get("can_approve"):
                can_approve = True

        return cls(
            user_id=user_id,
            session_id=session_id,
            roles=roles,
            allowed_sources=list(sources),
            allowed_actions=list(actions),
            can_approve=can_approve,
        )

    def can_read_source(self, source_type: str) -> bool:
        if "*" in self.allowed_sources:
            return True
        return source_type in self.allowed_sources

    def can_execute_action(self, action_name: str) -> bool:
        if "*" in self.allowed_actions:
            return True
        return action_name in self.allowed_actions

    def assert_can_read(self, source_type: str) -> None:
        if not self.can_read_source(source_type):
            raise PermissionError(f"User {self.user_id!r} cannot read source {source_type!r}")

    def assert_can_act(self, action_name: str) -> None:
        if not self.can_execute_action(action_name):
            raise PermissionError(f"User {self.user_id!r} cannot execute action {action_name!r}")
