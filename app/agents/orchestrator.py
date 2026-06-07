"""Orchestrator agent: classifies requests and routes to the correct workflow."""

from crewai import Agent

from app.agents.llm_factory import get_fast_llm

WORKFLOW_TYPES = ["SEARCH", "RESEARCH", "MONITOR", "ACTION", "MEMORY_UPDATE"]


def build_orchestrator() -> Agent:
    return Agent(
        role="Orchestrator",
        goal=(
            "Classify the user request into exactly one of: "
            f"{', '.join(WORKFLOW_TYPES)}. "
            "Then enforce permissions and select the appropriate workflow."
        ),
        backstory=(
            "You are the entry point for HERMES. You read every request, "
            "classify its intent, check permissions, and hand it to the right specialist crew. "
            "You never retrieve documents or generate answers yourself — you route and govern."
        ),
        llm=get_fast_llm(),
        verbose=True,
        allow_delegation=True,
        max_iter=3,
    )
