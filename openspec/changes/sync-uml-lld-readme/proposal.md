## Why

A full review of the keep-set docs shows hub prose (`system.md`, most of `ai.md` / `frontendguide.md` / README capabilities) is largely aligned after `align-docs-with-system`, but **UML diagrams**, **deep LLD call flows**, and **README discoverability** still describe a pre-fallback / pre-HITL / pre-dual-collection stack. Agents and humans who trust `docs/uml/` or LLD §4 as the contract will implement or explain the wrong LLM path, Compose services, and search shape.

## What Changes

- Retarget UML sources away from dead `src/docs/*` to `docs/documentation/lld.md` (and fold or keep `docs/uml/README.md` only as a thin pointer — deletions of retire-set files stay owned by in-flight `consolidate-docs`).
- Refresh UML / LLD diagrams and deep flows so they match live code: `acompletion_with_fallback` (not `acompletion_with_retry`), dual-collection semantic search (`notes_chunks` + `files_chunks`), Compose without default Grafana, HITL interrupt/resume/reject on the agent path, and observability depth (`dashnote_ai_*`, feedback, agent traces) in LLD §4.16+.
- Expand LLD §5 data-model notes for integrations tables and AI-era fields (`notes.tags`, file extract/summary/tags, `ai_threads.title`) without rewriting product schemas.
- Fix residual keep-set inaccuracies that contradict already-correct hubs: `rules.md` ARQ pool law (`ctx["arq_pool"]`), `ai.md` Observability footer (quality counters + feedback, not a SLO).
- Polish root `readme.md`: document `/integrations` briefly, widen the Documentation index (`auth.md`, `observe.md`, `lld.md` as appropriate), keep honesty on pending HTTPS / production-live.
- Optional FE note: SSE heartbeats in `frontendguide.md` for quiet-stream debugging.
- **Non-goals:** application code; deleting/merging the `consolidate-docs` retire-set; collapsing dual observe paths (still `consolidate-docs`); reopening `align-docs-with-system` hub HTTP-surface work already done; claiming production-live or mid-enterprise.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `canonical-docs`: UML (`docs/uml/`) and LLD deep flows MUST match live architecture (fallback LLM, dual collections, no default Grafana Compose, working doc paths, HITL on agent diagrams, metrics/feedback depth). Residual laws in `rules.md` / `ai.md` Observability MUST NOT contradict worker startup or serving L3.
- `portfolio-baseline`: Root README Documentation / architecture discoverability MUST surface integrations and key keep-set docs (`lld`, auth, observe as applicable) without claiming unverified production-live URLs.
- `frontend-developer-guide`: Frontend guide MUST mention SSE comment heartbeats (or an explicit pointer) so FE authors know quiet streams are kept alive through Nginx — without requiring UI changes for B-gate.

## Impact

- **Docs / OpenSpec context only** — no FastAPI, worker, schema, Nginx, or Compose behavior changes.
- Touched files (planned): `docs/uml/diagrams.md`, `docs/uml/README.md`, `docs/documentation/lld.md`, `docs/documentation/ai.md` (Observability footer), `docs/documentation/rules.md`, `docs/documentation/frontendguide.md` (SSE note), `readme.md`.
- Coordinate with `consolidate-docs`: this change fixes **accuracy**; that change owns **tree shrink / link rewrite / deletions**. Do not delete retire-set files here.
- Tenancy / chat≠agent / hard-vs-soft health: unchanged.
