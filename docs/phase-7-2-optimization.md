# Phase 7.2 Optimization And Reliability

Phase 7.2 focuses on real-use stability before Phase 8. It does not add Knowledge Base
management, deletion, re-index controls, cloud calls, OCR, or persistent chat memory.

## Router Behavior

GroundNote now routes app-level and invalid inputs before retrieval or model calls:

- greetings, thanks, and app-help messages return deterministic local responses;
- empty input returns a localized prompt to enter a question;
- unclear short inputs such as `A`, `?`, `asd`, `asdf`, and repeated characters return a friendly
  localized clarification message;
- short technical terms such as `W123`, `W124`, `R107`, `OM617`, `M104`, `CRC`, `NVH`, `HTTP`,
  `API`, and `VIN` are allowed through to retrieval;
- if no documents are ready, the answer explains whether the user should upload a document or wait
  for processing.

These paths do not load the embedding model, do not load the chat model, and do not perform
retrieval.

## Answer Quality Guardrails

The RAG prompt version is `grounded-rag-v2`. It asks for concise answers, natural Turkish when the
question is Turkish, compact citations, and stricter separation between related technical concepts.
For automotive documents, chassis/body codes and engine codes are treated as separate concepts
unless the question asks for both.

GroundNote also adds post-generation repetition protection. It detects repeated words, repeated
phrases, repeated citation markers, low-diversity tails, and overly long output. When possible, it
trims the answer to the last safe complete sentence while preserving a valid citation. If the
answer is unusable, one stricter regeneration is attempted. A second repeated output returns a
localized safe error.

## Citation Cleanup

Normal chat output uses compact source rendering. Duplicate source labels are suppressed, and
technical retrieval details are not shown in the normal answer flow. Citation IDs such as `[S1]`
remain mapped only from trusted retrieval metadata.

## Performance Changes

The default context budget is smaller:

- retrieval top-k: `3`;
- minimum score: `0.24`;
- maximum context characters: `2600`;
- maximum context chunks: `3`;
- maximum output tokens: `224`;
- temperature: `0.1`.

GroundNote skips chat generation when retrieval confidence is below the configured threshold. The
embedding service tracks whether the provider is already loaded, so sequential indexing and warm
retrieval avoid unnecessary reload calls in the same session. Memory saver still unloads after
operations.

## Image-Only PDF Behavior

PDFs with no extractable text are treated as unsupported for the MVP because OCR is not available.
They are not embedded and are not marked ready. The UI returns a localized message explaining that
text could not be extracted from an image-based PDF.

## Safe Performance Report

The internal performance report exposes only safe metadata such as duration, grounded/insufficient
status, retrieved/context/citation counts, model alias, and warning codes. It does not include the
query, prompt, document text, generated answer, vectors, paths, or hashes.

## Verification Notes

The normal non-Foundry test suite covers router bypasses, no-ready-document behavior, warm
embedding reuse, low-confidence retrieval skipping chat, repetition repair, compact citations,
Turkish chassis prompt constraints, OCR-safe messages, and safe performance metadata.

Manual Windows smoke should still verify real local model behavior with representative PDFs and
DOCX/TXT fixtures because local model latency and wording vary by hardware and cached model state.

Phase 7.2 manual Windows measurements on the current machine used cached Foundry Local models,
`MB-nomenclature.pdf`, `gecmisten-gelecege-otomobil-tasarimi.pdf`, a generated image-only PDF, and
a small TXT fixture:

| Operation | Measured time |
| --- | ---: |
| Small TXT indexing | 5.728 s |
| MB PDF indexing | 98.081 s |
| Turkish PDF indexing | 107.257 s |
| Image-only PDF rejection | 0.018 s |
| `A`, `?`, `asdf` invalid input | 0.000 s |
| Greeting | 0.000 s |
| Mercedes chassis answer, cold retrieval | 5.658 s |
| Mercedes chassis answer, warm retrieval | 0.437 s |
| Mercedes engine answer, warm retrieval | 0.466 s |
| Turkish design answer, warm retrieval | 0.430 s |
| Unrelated World Cup question | 0.546 s |
| Small TXT fact answer | 0.578 s |

The initial pre-fix manual run reproduced the core issue: grounded answers reached 79-140 s and
the unrelated World Cup question took 81.726 s because it reached chat generation. After Phase 7.2,
the unrelated path is stopped before chat generation, and the Mercedes/Turkish-design/small-TXT
cases use deterministic context answers with trusted citations.
