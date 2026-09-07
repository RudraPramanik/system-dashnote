## Why

`docs/documentation/qs.md` trains interviews on how *this* repo is built, but it does not cover the broader production AI/RAG/agent questions hiring loops ask: enterprise RAG on existing databases, latency, evals, failure modes, security, and system design. Candidates need a second, lengthy concept-clearance document that can pass a production AI engineering interview, not only a “how our app works” recap.

## What Changes

- Author a comprehensive interview Q&A at `docs/documentation/qs2.md` covering production AI engineering: RAG, retrieval, embeddings, agents, latency, evals, observability, security, cost, and enterprise integration.
- Treat `qs2.md` as a **concept + interview-passing gate**: each answer should be usable spoken, then go deep enough to survive follow-ups.
- Keep `qs.md` as the DashNoteSystem-specific talk track. Cross-link the two files; do not merge them.
- Length is expected and allowed. Prefer complete coverage over brevity.
- No application code, API, schema, or runtime behavior changes.

## Capabilities

### New Capabilities

- `ai-engineering-interview-qa`: A production-level AI/RAG/agent interview Q&A document at `docs/documentation/qs2.md` that covers concept clearance and hire-loop answers, complementary to `qs.md`.

### Modified Capabilities

- (none — existing product specs are unchanged; this is a new documentation capability)

## Impact

- **Docs:** Primary deliverable is `docs/documentation/qs2.md`. Light pointer from `qs.md` (and optionally README/docs index if a docs index already lists `qs.md`).
- **Consumers:** Interview prep, Upwork/client system-design calls, and concept-clearance review for production RAG/agent work.
- **APIs / code:** None. Answers may *reference* DashNoteSystem patterns as examples, but MUST remain generally applicable to enterprise AI systems.
- **Non-goals:** Changing chat/agent routes, eval harness code, HITL, GraphRAG implementation, or rewriting `qs.md`.
