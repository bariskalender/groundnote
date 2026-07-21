# Phase 7.2.2 — Section Retrieval and UI State Stability

Phase 7.2.2 is a corrective stabilization patch for the Phase 7 Streamlit interface and grounded
RAG path. It does not add Phase 8 Knowledge Base management, chat history, re-index controls, OCR,
cloud inference, or external telemetry.

## Changes

- Added section-title-aware filtering before RAG context assembly. When a question names a specific
  retrieved section or item, GroundNote prefers chunks from that section and drops conflicting
  nearby sections. Explicit comparison questions may use both named sections.
- Added a strong-entity coverage guard for obvious out-of-domain questions. If retrieved chunks do
  not contain the important named entities in the question, GroundNote returns insufficient evidence
  without loading the chat model.
- Hardened answer cleanup for empty bullets, citation-only bullets, repeated answer headings,
  unrequested bilingual tails, dangling endings, and known malformed-output quality markers.
- Updated deterministic routing so Turkish greetings such as `merhaba` stay Turkish even without
  Turkish-only characters.
- Changed overlapping UI operations to show a friendly busy message instead of a generic operation
  failure.
- Shortened the single-document remove confirmation wording.
- Set Streamlit to run headless from local configuration and kept browser usage statistics disabled.

## Privacy and Resource Notes

- No prompts, full documents, embeddings, generated answers, or user files are sent to external
  services.
- Normal deterministic shortcuts do not call Foundry Local models.
- The patch preserves the Phase 7.2.1 model lifecycle controls and does not introduce parallel
  chat/indexing model loads.
