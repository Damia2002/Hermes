"""Planner agent: produces a plan-and-execute decomposition for complex questions."""

from crewai import Agent

from app.agents.llm_factory import get_primary_llm


def build_planner() -> Agent:
    return Agent(
        role="Research Planner",
        goal=(
            "Decompose complex enterprise questions into an ordered list of retrieval steps. "
            "Each step must specify: what to search for, which source types to use, "
            "and what information is expected."
        ),
        backstory=(
            "You are a systematic analyst. When given a hard question, you break it into "
            "3–5 concrete retrieval sub-tasks rather than attempting everything at once. "
            "You write plans in plain numbered lists, not prose."
        ),
        llm=get_primary_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
