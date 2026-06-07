---
name: change-monitoring
description: Detect and report material changes to a monitored enterprise topic.
allowed_tools:
  - search_knowledge
  - compare_snapshots
---

# Procedure

1. Run the saved monitoring query to retrieve the current evidence set.
2. Compare the current `doc_id` list against the previous snapshot stored in the database.
3. Classify the change:
   - `NEW_INFORMATION`: new documents appeared that are relevant to the topic.
   - `CHANGED_INFORMATION`: existing documents have been updated (newer timestamp, different content).
   - `DOCUMENT_REMOVED`: previously relevant documents are no longer returned.
   - `CONFLICT_DETECTED`: new documents contradict existing evidence.
   - `NO_MATERIAL_CHANGE`: no significant difference detected.
4. For material changes, generate a concise alert:
   - What changed (old value vs. new value, if extractable).
   - Which documents are involved (`doc_id` for both old and new).
   - Recommended action (e.g., review, escalate, update downstream systems).
5. Do not generate an alert for `NO_MATERIAL_CHANGE`.
6. Save the new snapshot to the database for the next comparison.
