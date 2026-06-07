# MEMORY.md — HERMES Durable User Preferences

This file contains only user-approved, durable notes for HERMES.
Conversation logs are NOT automatically saved here.

---

## Global Defaults

- Always display evidence alongside confidence labels — never show "high confidence" without sources.
- Always report conflicting documents explicitly rather than picking one silently.
- Never execute write actions (Jira, email) without explicit human approval.
- Prefer concise executive summaries unless `response_mode = detailed` is requested.
- When information is not found in the knowledge base, say so clearly — do not invent an answer.

---

## Adding Entries

Use the HERMES Memory page in the Streamlit UI, or POST to `/v1/memory`:

```json
{
  "user_id": "your-user-id",
  "content": "Prefer answers in bullet points.",
  "memory_type": "episodic",
  "tags": ["preference", "format"]
}
```

Memory types:
- `episodic` — user preferences and past interactions
- `semantic` — domain facts about the enterprise
- `procedural` — reusable standard operating procedures

---

_Managed by HERMES. Last updated: see git history._
