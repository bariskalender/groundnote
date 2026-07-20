# RAG Generation

GroundNote connects hybrid local retrieval to local chat generation. It is local-only and uses
session-only UI history rather than persistent chat storage.

## Flow

1. Validate and normalize the user question.
2. Resolve the response language as Turkish or English.
3. Route greetings, thanks, and app-help messages before RAG.
4. Run hybrid retrieval once for document questions.
5. Select bounded retrieved chunks as untrusted context.
6. Build separated system and user prompts with prompt version `grounded-rag-v1`.
7. Generate with Microsoft Foundry Local chat.
8. Parse the supported/insufficient status and validate citation IDs.
9. Return a grounded answer or a deterministic insufficient-evidence response.

## Model Selection

The primary chat model is `phi-3.5-mini`; the low-resource fallback remains `qwen2.5-0.5b`.
The provider uses Foundry Local only. If direct SDK loading fails in the installed preview runtime,
the provider may use the OpenAI-compatible Foundry daemon on loopback for the same local model
variant. No cloud fallback is implemented.

## Context Selection

RAG context preserves retrieval score order, skips empty chunks, suppresses duplicate chunk IDs, and
assigns citation IDs in final context order: `S1`, `S2`, `S3`, and so on. Complete chunks are used;
GroundNote stops before exceeding the configured context character limit instead of cutting chunks.

Defaults:

- retrieval top-k: `5`
- minimum score: `0.20`
- maximum context characters: `6000`
- maximum context chunks: `5`
- maximum output tokens: `512`
- temperature: `0.1`

## Groundedness And Insufficient Evidence

`grounded=True` only when retrieval returns usable context, chat generation succeeds, the model
declares `STATUS: supported`, and the answer contains at least one valid citation from the supplied
context.

If no usable context exists, GroundNote does not call the chat model. It returns a deterministic
message explaining that the answer was not found in indexed documents. This is not a system error.

If the model receives retrieved context but explicitly states in English or Turkish that the
sources do not contain enough evidence, GroundNote also converts that output to the deterministic
insufficient-evidence result. Any citation appended to that refusal is removed so it cannot be
presented as a grounded-success answer.

Greetings, thanks, and app-help messages are deterministic and do not load embedding or chat
models.

## Scope And Limitations

- No final Streamlit chat UI is implemented in Phase 6.
- No persistent conversation memory is implemented.
- No history-aware query rewriting is implemented.
- Local models can still make mistakes; users should verify important answers against source
  documents.
