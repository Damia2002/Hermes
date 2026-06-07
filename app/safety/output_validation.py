"""Output schema validation and sensitive-field redaction."""

import re
from typing import Any

from pydantic import BaseModel, Field

REDACT_PATTERNS: list[re.Pattern] = [
    re.compile(r"(api[_-]?key|secret|password|token|credential)[=:\s]+\S+", re.I),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
]


def redact_sensitive(text: str) -> str:
    for pattern in REDACT_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class SourceReference(BaseModel):
    doc_id: str
    title: str
    source_type: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class SupportedClaim(BaseModel):
    claim: str
    supporting_doc_ids: list[str]


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    claims: list[SupportedClaim] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    information_not_found: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    human_note: str | None = None

    def validate_claims(self) -> list[str]:
        """Return doc_ids referenced in claims but absent from sources."""
        source_ids = {s.doc_id for s in self.sources}
        orphans: list[str] = []
        for claim in self.claims:
            for doc_id in claim.supporting_doc_ids:
                if doc_id not in source_ids:
                    orphans.append(doc_id)
        return orphans

    def redact(self) -> "ResearchResponse":
        return self.model_copy(
            update={
                "summary": redact_sensitive(self.summary),
                "claims": [
                    SupportedClaim(
                        claim=redact_sensitive(c.claim),
                        supporting_doc_ids=c.supporting_doc_ids,
                    )
                    for c in self.claims
                ],
            }
        )


def validate_response(response: dict[str, Any], retrieved_doc_ids: set[str]) -> ResearchResponse:
    """Parse and validate an agent response dict.

    Raises ValueError if any claim references a document not in retrieved_doc_ids.
    """
    parsed = ResearchResponse.model_validate(response)
    orphans = parsed.validate_claims()
    if orphans:
        raise ValueError(f"Response references unretrieved documents: {orphans}")
    return parsed.redact()
