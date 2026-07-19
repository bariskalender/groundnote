# GroundNote Chunking Strategy

Phase 4 adds deterministic text chunking before embeddings are generated. Chunking is needed
because study documents are usually too large to embed or cite as one block. GroundNote prepares
smaller, ordered chunks that can later be embedded and searched locally.

## MVP Defaults

- Target size: 900 characters.
- Maximum size: 1400 characters.
- Overlap: 120 characters.
- Minimum size: 120 characters.
- Version: `hybrid-recursive-v1`.

These are conservative MVP choices for local study documents, not universal constants.

## Hybrid Recursive Order

The chunker uses existing parsed document metadata first, then falls back to smaller text
boundaries only when necessary:

1. Parsed section boundaries.
2. PDF page boundaries through preserved `page_number` metadata.
3. DOCX and Markdown heading boundaries through preserved `section_title` metadata.
4. Paragraph boundaries using normalized blank lines.
5. Lightweight sentence boundaries for `.`, `!`, and `?`.
6. Whitespace boundaries.
7. Hard character splits for pathological long unbroken text.

The implementation is deterministic. The same parsed document and settings produce the same chunk
order, chunk text, source metadata, warnings, and sequential chunk indexes.

## Page And Heading Preservation

PDF page numbers are preserved from the parser. The MVP chunker avoids merging content across page
boundaries, so a chunk does not claim a page number that does not represent its source content.

DOCX and Markdown headings are preserved as section titles where the parser provides them. Overlap
and short-fragment merging avoid crossing unrelated heading boundaries.

## Paragraphs, Sentences, And Fallbacks

Paragraphs are kept together when possible and adjacent paragraphs are combined until near the
target size without exceeding the maximum. Fenced Markdown code blocks are treated as coherent
paragraph units where practical.

The sentence splitter is intentionally lightweight. It handles common English and Turkish sentence
endings, avoids obvious decimal-number breaks, and skips several common abbreviations. It is not a
full linguistic parser.

If a sentence or unit is still too large, the chunker splits by whitespace. If one token is longer
than the maximum size, it is hard-split deterministically with a warning. No characters are silently
dropped.

## Overlap

Overlap is added as a short prefix from the end of the previous compatible chunk. It is only applied
between chunks with the same page number and section title. It is skipped when it would exceed the
maximum size, duplicate the entire previous chunk, or cross a PDF page or unrelated heading
boundary.

## Short Fragments

Fragments smaller than the configured minimum are merged when safe:

1. Previous compatible fragment on the same page and section.
2. Next compatible fragment on the same page and section.
3. Otherwise kept standalone with a warning.

The MVP does not merge across PDF page boundaries merely to satisfy the minimum size.

## Token Estimate

Phase 4 does not add a tokenizer dependency. Token counts use the coarse heuristic:

```text
estimated_tokens = max(1, round(character_count / 4))
```

This value is approximate and is not used for strict model context enforcement.

## Known Limitations

- Sentence splitting is heuristic and may not match a full NLP tokenizer.
- Very large code blocks can still be split if they exceed the maximum size.
- Overlap is character-based, not token-based.
- Phase 4 does not generate embeddings, perform semantic search, or call Foundry Local models.
