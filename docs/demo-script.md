# GroundNote 1.0.0 Demo Script

This 3–5 minute flow uses only the original fictional material in
`examples/groundnote-demo-handbook.md`. Start with an empty isolated GroundNote data directory or
remove any prior demo copy from the Knowledge Base. Do not use private documents in a recording.

## 1. Introduce the Problem

**Say:** Students often need to search and question long course documents, but those files may be
private. Cloud assistants can be convenient, yet they create an unwanted data boundary.

**Show:** The repository README title and one-line description.

**Expected outcome:** The audience understands that GroundNote is a local study assistant, not a
general-purpose cloud chatbot.

## 2. Explain Local Processing

**Say:** GroundNote parses documents, creates embeddings, stores its index, retrieves evidence, and
generates answers on this computer through Microsoft Foundry Local. Initial tools and model files
must be downloaded, but cached inference uses the local runtime. There is no cloud AI fallback or
telemetry.

**Show:** The privacy note in the UI or the README architecture summary.

**Expected outcome:** The local/offline boundary is explicit without claiming that installation
itself requires no internet.

## 3. Launch GroundNote

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_groundnote.ps1
```

**Show:** The chat-first home screen, sidebar, Foundry status, and settings popover.

**Expected outcome:** The application responds on a loopback URL. No model loads merely to render
the interface.

## 4. Upload the Safe Sample

Select `examples/groundnote-demo-handbook.md` in the one-file uploader.

**Say:** GroundNote accepts one supported document at a time. The browser MIME type is not trusted;
the backend validates the filename, size, signature, format limits, and SHA-256 duplicate status.

**Expected outcome:** Processing begins automatically. There is no Process button or background
queue.

## 5. Show Indexing Stages

Point out the real stage labels such as validating, extracting, chunking, and embedding. Explain
that chat is disabled while indexing to avoid overlapping CPU-bound local model work.

**Expected outcome:** The document becomes **Ready** only after its chunks, float32 embeddings,
model metadata, and FTS rows pass the integrity check. Do not quote a fixed completion time because
hardware and cache state change it.

## 6. Ask an Answerable Question

Ask:

> Why does the team calculate five-minute medians while retaining the raw samples?

**Expected outcome:** GroundNote explains that medians reduce the influence of individual noisy
samples while raw 30-second readings remain available for auditing.

## 7. Show Citations

Point to the inline source ID and the trusted source card below the answer.

**Say:** The model may emit only IDs from the supplied context. GroundNote maps those IDs back to
the safe filename and section metadata from retrieval; it does not trust model-generated filenames.

**Expected outcome:** At least one citation points to the demonstration handbook and a relevant
section. If the local model cannot produce a valid cited answer, report that honestly instead of
editing the screenshot or result.

## 8. Ask an Unsupported Question

Ask:

> What orbit does the Lantern Lab weather satellite use, and when was it launched?

**Expected outcome:** GroundNote reports insufficient evidence with no citations. It must not invent
a satellite, orbit, or launch date.

## 9. Show the Knowledge Base

Expand the Knowledge Base entry for `groundnote-demo-handbook.md`.

**Show:** Ready status, type, chunk count, and available section/page metadata. Mention the per-file
Re-index and confirmed Remove controls.

**Expected outcome:** Only safe metadata is visible. No managed UUID filename, hash, vector, raw
path, or document text appears.

## 10. Explain Session Behavior

Choose **New chat** after the answer demonstration.

**Expected outcome:** Conversation messages clear, while the indexed handbook remains in the
Knowledge Base. Chat history is not persisted to SQLite.

## 11. Close with Architecture and Limitations

Open `docs/architecture.md`.

**Say:** The application uses Streamlit, small Python services, SQLite FTS5, NumPy cosine
similarity, and Foundry Local provider adapters. CPU embedding is the current indexing bottleneck.
Indexing is synchronous, only one file is uploaded at a time, chat is unavailable during indexing,
and there is no OCR, persistent queue, native signed installer, or bundled model.

**Expected outcome:** The audience sees both the completed 1.0.0 scope and the intentionally deferred
work.

## Cleanup

Remove the demo document through the Knowledge Base if the demonstration should leave no local
data, then stop the scoped session:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_groundnote.ps1 -StopFoundry
```

Confirm the listener is gone and `foundry status` reports zero GroundNote-loaded models. Never
delete a user's original document during cleanup.
