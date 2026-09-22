## Context

See proposal.md — Why. Hub docs (`system.md` and most of `ai.md` / README capabilities) already reflect L3 feedback and Compose honesty via `align-docs-with-system`. Deep LLD ASCII (§4.12–4.18) and `docs/uml/diagrams.md` still show `acompletion_with_retry`, single-collection search, Grafana-on-Compose, and dead `src/docs/` sources. In-flight `consolidate-docs` owns tree deletions and dual-observe collapse; this design only patches accuracy on surviving files.

Ground truth for edits (read, do not invent):
- LLM: `shared.llm.fallback.acompletion_with_fallback` (agent + RAG)
- Search: `WorkspaceVectorSearch` → `notes_chunks` + `files_chunks` merge
- Compose: `docker-compose.yml` (no Grafana service)
- HITL: agent interrupt → `approval_required` → resume/reject
- Worker: `ctx["arq_pool"]` set on ARQ startup
- SSE: `ai_routes/sse_heartbeat.py` comment heartbeats

## Goals / Non-Goals

**Goals:**
- Make UML + LLD deep flows trustworthy for implementers/interviewers.
- Keep README stranger-discoverable (integrations + keep-set doc index) without false production claims.
- Close small law/footer contradictions (`rules.md`, `ai.md` Observability).
- Leave a clear handoff to `consolidate-docs` for deletes.

**Non-Goals:**
- Regenerating PlantUML from a code generator (manual mermaid/ASCII update is enough).
- Changing runtime behavior, env defaults, or OpenAPI.
- Deleting `observability.md`, blueprint slices, or `ship-plan.md`.
- Full rewrite of LLD §1–§3 composition already fixed by align.

## Decisions

### D1 — Edit UML in place; do not invent a second diagram home
**Choice:** Update `docs/uml/diagrams.md` (and thin `docs/uml/README.md` source pointers) as the diagram surface; keep LLD ASCII as the narrative twin and align both.
**Alternatives:** Move all diagrams into `lld.md` only — rejected; README and portfolio already link `docs/uml/diagrams.md`.
**If `consolidate-docs` later folds README into `diagrams.md`:** this change’s content survives; only the thin README file may disappear later.

### D2 — Prefer named live helpers over obsolete retry wording
**Choice:** Diagrams and LLD MUST say wall-clock + candidate-list fallback (`acompletion_with_fallback` / documented settings `LLM_MODEL` + `LLM_MODEL_FALLBACKS`). Do not keep `acompletion_with_retry` as the primary edge even as a footnote alias unless code still exports that name as the public entry.
**Alternatives:** Dual-label both — rejected; dual names perpetuate the stale path.

### D3 — Scope README polish tightly
**Choice:** Add one integrations bullet (or capability row) + Documentation links to `lld.md`, `auth.md`, `observe.md`; do not expand into a full ops handbook.
**Alternatives:** Full README restructure — rejected; portfolio pitch already works.

### D4 — Sequence vs `consolidate-docs`
**Choice:** Implement this change independently on keep-set files. Do not wait for consolidate deletes. After both land, link rewrite is consolidate’s job for retire-set paths.
**Alternatives:** Fold P1 into consolidate task 1.5 — rejected; consolidate has 0 tasks done and different ownership; accuracy should not block on tree surgery.

### D5 — Validation is link + string audit, not pytest
**Choice:** After edits, grep for forbidden stale tokens (`src/docs/`, `acompletion_with_retry`, `grafana :3001` as local Compose) in touched files and confirm Compose list matches `docker-compose.yml` services.
**Alternatives:** Add a CI doc-lint job — out of scope for this change.

## Risks / Trade-offs

- **[Risk] consolidate-docs deletes `docs/uml/README.md` after we update it** → Mitigation: put authoritative content in `diagrams.md`; README stays a pointer only.
- **[Risk] LLD ASCII and UML diverge again after future AI changes** → Mitigation: specs require both UML and LLD deep flows to stay coherent; tasks include a cross-check checklist.
- **[Risk] Over-documenting integrations in README implies product maturity** → Mitigation: one-line + link to `inbound-channels.md`; keep production-live pending.

## Migration Plan

1. Apply doc/UML edits in a single PR/commit set (docs only).
2. No deploy / rollback needed beyond reverting the markdown.
3. Optional follow-up: apply or resume `consolidate-docs` for tree shrink.

## Open Questions

None — dual-observe retention and retire-set deletes remain explicitly owned by `consolidate-docs`.
