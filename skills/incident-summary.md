---
name: incident-summary
description: Summarise an incident using enterprise evidence from multiple sources.
allowed_tools:
  - search_knowledge
  - retrieve_document
---

# Procedure

1. Identify the incident by name, ticket ID, or date range.
2. Retrieve operational documents: runbooks, deployment logs, Jira tickets, Slack threads.
3. Retrieve communication documents: emails, meeting transcripts, post-mortems.
4. Construct a timeline: what happened, when, who was involved.
5. Separate confirmed facts (with `doc_id`) from unresolved claims.
6. Note any conflicting accounts of the incident.
7. Cite every material claim with a `doc_id`.
8. Conclude with open questions and recommended follow-up actions.
