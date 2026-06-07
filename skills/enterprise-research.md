---
name: enterprise-research
description: Search and synthesise enterprise knowledge across multiple internal sources.
allowed_tools:
  - search_knowledge
  - retrieve_document
---

# Procedure

1. Classify the question as simple (single source, factoid) or complex (cross-source, multi-step).
2. For complex questions, decompose into 3–5 ordered retrieval sub-tasks.
3. Run hybrid search for each sub-task; record the `doc_id` for every passage.
4. Deduplicate passages that appear across sub-tasks.
5. Synthesise a structured response: summary, claims with `doc_id` citations, source list.
6. Report any conflicting information explicitly — never suppress it.
7. If the information is not present in the retrieved documents, set `information_not_found = true`.
