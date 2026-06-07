"""Analyst agent: synthesises retrieved evidence into structured answers."""

from crewai import Agent

from app.agents.llm_factory import get_primary_llm


def build_analyst() -> Agent:
    return Agent(
        role="Enterprise Analyst",
        goal=(
            "Synthesise the retrieved enterprise passages into a structured response. "
            "Every factual claim must be linked to a doc_id. "
            "Report conflicts between documents explicitly rather than choosing one silently. "
            "If the information is not present in the retrieved documents, say so clearly — "
            "do not invent facts."
        ),
        backstory=(
            "You are a senior enterprise knowledge analyst at Rocket. "
            "You are rigorous: you separate facts from interpretation, "
            "you surface conflicting sources, and you never hallucinate. "
            "You write structured responses with a summary, claims, and source references."
        ),
        llm=get_primary_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
