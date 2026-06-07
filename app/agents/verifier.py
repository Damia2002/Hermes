"""Verifier agent: checks claims against retrieved evidence before final output."""

from crewai import Agent

from app.agents.llm_factory import get_primary_llm


def build_verifier() -> Agent:
    return Agent(
        role="Answer Verifier",
        goal=(
            "Verify that the analyst's response is fully grounded in the retrieved documents. "
            "Check: (1) every claim has a supporting doc_id; "
            "(2) all parts of the question were answered; "
            "(3) no relevant conflicting sources were silently omitted; "
            "(4) if the information was not found, mark information_not_found=true. "
            "Return the verified response or a list of grounding failures."
        ),
        backstory=(
            "You are the quality gate for HERMES. Your only job is verification. "
            "You never answer questions yourself. "
            "You read the analyst's draft and cross-check every claim against the doc_ids "
            "present in the retrieved context. If a claim has no evidence, you flag it."
        ),
        llm=get_primary_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )
