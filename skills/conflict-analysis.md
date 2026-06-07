---
name: conflict-analysis
description: Identify and explain contradictions between documents in the knowledge base.
allowed_tools:
  - search_knowledge
  - retrieve_document
---

# Procedure

1. Retrieve all documents relevant to the contested topic.
2. Extract the specific claim from each document (date, value, procedure, assignment).
3. Compare claims across documents and identify those that directly contradict each other.
4. For each conflict, record: document A `doc_id`, document B `doc_id`, the conflicting claims, and timestamps if available.
5. Determine which document is more recent or authoritative (by timestamp or source type).
6. Present both versions to the user without picking one — let the user decide which to act on.
7. Recommend that the user flag the conflict for resolution if the discrepancy is operational.
