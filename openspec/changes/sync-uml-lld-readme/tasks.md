## 1. UML source and Compose honesty

- [x] 1.1 Retarget `docs/uml/README.md` (and any source notes in `docs/uml/diagrams.md`) from dead `src/docs/*` to `docs/documentation/lld.md` / working `docs/` paths
- [x] 1.2 Update Compose deployment diagram in `docs/uml/diagrams.md` to match `docker-compose.yml` (no default Grafana `:3001` service)

## 2. UML AI / search / LLM flows

- [x] 2.1 Update semantic search diagram for dual-collection merge (`notes_chunks` + `files_chunks`) with workspace/RBAC filter
- [x] 2.2 Replace agent / shared-LLM `acompletion_with_retry` edges with `acompletion_with_fallback` (wall-clock + candidate list)
- [x] 2.3 Add HITL interrupt → `approval_required` → resume/reject to the agent sequence (keep `/ai/chat*` separate)
- [x] 2.4 Refresh memory/thread diagram notes for auto-title / `title` where the class diagram is shown

## 3. LLD deep flows and entities

- [x] 3.1 Patch LLD RAG / agent / shared-LLM sections (§4.13, §4.15, §4.18 or equivalents) to use fallback completion
- [x] 3.2 Patch LLD semantic search / retrieval ASCII for dual collections
- [x] 3.3 Deepen LLD observability (§4.16) for `dashnote_ai_*`, feedback, and agent-turn tracing — not a production SLO or hard `/health` gate
- [x] 3.4 Expand LLD data-model (§5) for integrations persistence and AI-era fields (tags, file extract/summary, thread title)

## 4. Residual keep-set + README + FE

- [x] 4.1 Fix `docs/documentation/rules.md` ARQ pool law so `ctx["arq_pool"]` matches worker startup
- [x] 4.2 Tighten `docs/documentation/ai.md` Observability footer (`dashnote_ai_*`, feedback; not a SLO)
- [x] 4.3 Polish `readme.md`: integrations mention + Documentation links to `lld.md`, `auth.md`, `observe.md` (keep HTTPS production-live pending)
- [x] 4.4 Add SSE heartbeat/comment-frame note to `docs/documentation/frontendguide.md` (ignore for render; not a B-gate item)

## 5. Verify

- [x] 5.1 Grep touched docs for forbidden stale tokens (`src/docs/`, `acompletion_with_retry` as live path, Grafana as default Compose) and fix any remaining hits in scope
- [x] 5.2 Spot-check UML ↔ LLD ↔ `system.md`/`ai.md` for coherence on fallback, dual search, HITL, and Compose; do not delete files owned by `consolidate-docs`
