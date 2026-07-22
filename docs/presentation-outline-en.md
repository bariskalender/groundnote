# GroundNote Presentation Outline (English)

## Slide 1 — The Problem

- Students need fast answers from long, private study documents.
- Cloud assistants can move documents and questions outside the user's machine.
- Goal: a clear local workflow with evidence, not an unrestricted chatbot.

## Slide 2 — Project Goal and Scope

- Private, offline-first RAG study assistant.
- PDF, DOCX, TXT, and Markdown.
- English/Turkish answers, citations, and a local Knowledge Base.
- Windows 11 primary target; portfolio-quality desktop application.

## Slide 3 — Local RAG in One Diagram

- Validate and parse → chunk → embed → store.
- Embed question → hybrid retrieve → bounded prompt → local answer.
- Validate citation IDs and render trusted source metadata.

## Slide 4 — Implemented Architecture

- Streamlit UI and application context.
- Python service boundaries and Foundry-neutral providers.
- SQLite metadata/FTS5/float32 BLOBs plus NumPy cosine similarity.
- Microsoft Foundry Local for embedding and chat.

## Slide 5 — Secure Document Ingestion

- SHA-256 duplicate detection and managed copies.
- Page/section metadata preserved through deterministic chunking.
- PDF page/text limits and DOCX ZIP/XML preflight.
- Ready only after committed index-integrity verification.

## Slide 6 — Retrieval and Answer Generation

- Lexical FTS5 and semantic vector ranking.
- Section/title and strong-entity checks reduce false grounding.
- Retrieved content is untrusted evidence, never instructions.
- Citation-free refusal when evidence is insufficient.

## Slide 7 — Privacy and Resource Safety

- No cloud inference, telemetry, analytics, or persistent prompt logs.
- Documents, embeddings, questions, answers, and logs remain local.
- One GroundNote-owned chat model; embedding/chat handoff prevents overlap.
- One-file synchronous indexing; chat blocked during indexing.

## Slide 8 — Testing and Performance

- Unit tests use fake providers; Foundry tests remain explicit.
- Lint, format, strict typing, regression, coverage, UI, setup, and release smokes.
- CPU embedding is the measured bottleneck: 82.300 s of an 83.833 s 121-chunk run.
- Measurements are machine/workload specific, not guarantees.

## Slide 9 — Live Demo

- Upload the fictional Lantern Lab handbook.
- Ask an answerable question and inspect citations.
- Ask the unsupported satellite question and observe refusal.
- Show Knowledge Base and New chat behavior.

## Slide 10 — Lessons, Limits, and Future Work

- Simple boundaries made preview-SDK and privacy changes containable.
- Current limits: no OCR, background queue, persistent history, or native installer.
- Future ideas: cancellation, durable indexing, OCR, acceleration, macOS validation, signing.
- GroundNote 1.0.0 completes the intended portfolio scope.
