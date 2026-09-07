## Context

`docs/documentation/qs.md` is a DashNoteSystem-specific interview talk track (`They ask → You answer`). `docs/documentation/qs2.md` is empty. See `proposal.md` for why a second document is needed; see `specs/ai-engineering-interview-qa/spec.md` for the coverage contract.

This change is documentation only. Constraints: do not merge into `qs.md`; do not change APIs or runtime behavior; DashNoteSystem may appear only as a labeled example.

## Goals / Non-Goals

**Goals:**

- One long markdown file at `docs/documentation/qs2.md` that a candidate can study as both an interview script and a concept-clearance gate.
- A locked section map so apply work fills every production topic the spec requires, including enterprise RAG-on-existing-DB and RAG/agent latency.
- A repeatable answer shape: short spoken answer first, then mechanism / tradeoff / failure-mode depth.

**Non-Goals:**

- Rewriting `qs.md` beyond a short cross-link.
- Implementing RAG, agents, evals, HITL, or GraphRAG in code.
- Turning the doc into a copy of `ai.md` / `system.md` (point to those for this repo; keep `qs2.md` general).
- Splitting into multiple files in this change. Length in one file is acceptable.

## Decisions

### D1. Keep one file, match `qs.md` navigation, extend the answer shape

**Choice:** Write everything in `qs2.md`. Use a title, purpose, table of contents, numbered sections, and `### Question` headings like `qs.md`. Inside each answer, use two layers:

1. **Spoken** — 30–60 seconds, hire-loop cadence.
2. **If they probe** — mechanism, tradeoffs, failure modes, what to measure.

**Why:** Spec requires dual use (spoken + follow-up depth). Matching `qs.md` navigation keeps the docs set consistent; the extra layers are the concept-clearance gate.

**Alternatives considered:** Flatten to short answers only (fails the concept-gate requirement). Split into many topic files (harder to study as one interview pass). Copy `qs.md` 1:1 format with no spoken/probe split (harder to practice out loud).

### D2. Section map (locked TOC)

Write these sections in this order. Each section is multiple Q&A blocks, not a lecture.

| # | Section | Must include |
|---|---------|----------------|
| 0 | How to use this doc | Dual purpose, format, pointer to `qs.md`, “length is expected” |
| 1 | LLM building blocks | Tokens, context window, temperature, prompting vs weights, structured output |
| 2 | Embeddings & chunking | What embeddings are, chunk size/overlap, metadata, embedding drift |
| 3 | RAG architecture | Index → retrieve → augment → generate; naive vs production RAG |
| 4 | RAG on an existing enterprise system / DB | **Required.** Source of truth stays in OLTP/warehouse; CDC/jobs for sync; don’t dump the DB; SQL for facts + vectors for unstructured; permission-aware retrieval |
| 5 | Retrieval quality | Chunking, embeddings, hybrid search, rerank, query rewrite, filters, citation |
| 6 | Vector stores & search backends | Dedicated vector DB vs pgvector vs OpenSearch; filters before ANN |
| 7 | Indexing, sync, and freshness | Incremental index, deletes, embed lag, idempotent upserts |
| 8 | RAG chat vs agents | **Required.** Coexistence; when each wins; don’t default to agents |
| 9 | Agent design | Tools, loops, memory, HITL, blast radius, graph vs free-form ReAct |
| 10 | Latency | **Required.** TTFT vs E2E; streaming; cache; smaller models; parallel retrieve; fewer hops |
| 11 | Cost & capacity | Token cost, caching, batch embed, rate limits, routing |
| 12 | Security, tenancy, prompt injection | Filters from auth identity; injection; tool permissions; PII; citations |
| 13 | Evaluation | Goldens, retrieval vs generation, online eval, honesty about demo vs prod |
| 14 | Observability | Traces, prompts, retrieval sets, cost/latency, user feedback |
| 15 | Failure modes & production ops | Empty retrieval, provider 503, embed lag, fallbacks, circuit breakers |
| 16 | Streaming & UX | SSE/tokens, partial answers, cancel, citation timing |
| 17 | Memory & conversations | Thread history vs RAG context vs checkpoints; summarization |
| 18 | Fine-tuning vs RAG vs agents | When each is the right lever |
| 19 | System-design whiteboard | End-to-end production RAG design; scale numbers; SLOs |
| 20 | Counter-questions | **Required.** At least RAG vs fine-tune, chat vs agent, vector DB vs SQL |

Additional high-value questions that MUST appear somewhere (may live in the sections above rather than new headings): how to add RAG without rewriting the monolith; hybrid retrieval; multi-tenant RAG; grounding/hallucination; tool-calling safety; caching layers (embedding, retrieval, prompt, semantic); model routing; eval-driven improvement.

### D3. Example policy

**Choice:** Default answers are vendor-neutral and enterprise-shaped. When a DashNoteSystem pattern is a clean illustration (JWT `workspace_id` filters on Qdrant, chat vs agent coexistence, ARQ indexing), add a short **Example (DashNoteSystem):** note. Never present it as the only valid design.

**Why:** Spec forbids treating one product as the architecture. Interviewers still like “I shipped this.”

**Alternatives considered:** Zero repo references (weaker for this candidate’s talk track). Make `qs2.md` another repo tour (duplicates `qs.md`).

### D4. Cross-links only; no README rewrite unless already listing `qs.md`

**Choice:** Add a one-line pointer in the `qs.md` header to `qs2.md`. Reciprocal pointer in `qs2.md`. Do not rewrite README unless it already enumerates `qs.md` as a job-prep doc.

**Why:** Spec requires cross-links; README churn is out of scope unless discoverability is already there.

### D5. Depth over length limits

**Choice:** Prefer complete answers and extra follow-ups. No artificial section-size cap. Avoid padding: every block must be a real interview question.

**Why:** The user explicitly allowed a long file and asked for production-level passing docs.

## Risks / Trade-offs

- **[Risk] File becomes unreadable** → Mitigation: numbered TOC, consistent `###` questions, Spoken / If they probe split, no essay-only sections.
- **[Risk] Overlaps `qs.md` and confuses which to study** → Mitigation: header pointers; `qs2.md` stays general; repo bits labeled Example.
- **[Risk] Answers go stale vs this repo** → Mitigation: general answers first; examples are optional illustrations, not source of truth for product behavior (`qs.md` / `ai.md` remain canonical for the app).
- **[Risk] Too theoretical, fails “how would you do it in our company?”** → Mitigation: Section 4 and 19 are concrete playbooks (existing DB, sync, ACL, SLOs).
- **[Trade-off] One huge file vs many files** → One file wins for interview study; split later only if navigation fails.

## Migration Plan

1. Author `qs2.md` to the locked TOC (can be written section-by-section).
2. Add the `qs.md` header pointer.
3. Rollback: delete `qs2.md` content / revert the `qs.md` one-liner. No runtime rollback.

## Open Questions

None. Remaining editorial choices (exact question wording, extra follow-ups inside a section) do not change specs, approach, or the task breakdown.
