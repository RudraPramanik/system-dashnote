## ADDED Requirements

### Requirement: UML diagrams match live architecture and working sources
`docs/uml/diagrams.md` (and any UML index such as `docs/uml/README.md`) MUST document architecture that matches the running system: dual-collection semantic search (`notes_chunks` and `files_chunks` merged under RBAC/`workspace_id`), shared LLM completion via wall-clock + candidate fallback (not a sole retry helper as the live path), LangGraph agent HITL (`approval_required` then resume/reject) coexisting with fast RAG chat, and local Compose services without Grafana as a default `docker compose` service. UML sources MUST point at `docs/documentation/lld.md` (or other existing `docs/` paths). They MUST NOT cite `src/docs/` as if those files still exist.

#### Scenario: UML source paths resolve
- **WHEN** a reader opens `docs/uml/diagrams.md` or `docs/uml/README.md`
- **THEN** documented sources target existing paths under `docs/`
- **AND** no UML index presents `src/docs/lld.md` or `src/docs/system.md` as current locations

#### Scenario: Search diagram is dual-collection
- **WHEN** a reader follows the semantic search diagram
- **THEN** both notes and files vector collections appear in the retrieval path
- **AND** workspace/RBAC filtering remains on the search path

#### Scenario: Agent and LLM diagrams use fallback and HITL
- **WHEN** a reader follows agent or shared-LLM diagrams
- **THEN** completion is shown via the fallback candidate path
- **AND** mutation tools show an interrupt / approval gate before resume or reject
- **AND** `/ai/chat*` remains a separate path from `/ai/agent*`

#### Scenario: Compose diagram excludes default Grafana
- **GIVEN** `docker-compose.yml` does not start Grafana
- **WHEN** a reader follows the Compose deployment diagram
- **THEN** they MUST NOT be told Grafana on `:3001` is part of default local Compose

### Requirement: LLD deep flows match fallback, dual search, and serving observability
Deep call-flow sections of `docs/documentation/lld.md` (RAG, agent, shared LLM, observability) MUST match live behavior: RAG and agent completions go through fallback, semantic search covers notes and files collections, and observability documents both `dashnote_api_*` and `dashnote_ai_*` plus optional feedback / agent-turn tracing without calling those a production SLO or the hard `/health` gate. The LLD data-model overview MUST mention inbound/integration persistence and AI-era content fields (tags, file extract/summary, thread title) at summary level.

#### Scenario: RAG and agent LLD use fallback
- **WHEN** a reader follows LLD RAG or agent completion steps
- **THEN** they see the fallback completion path
- **AND** they MUST NOT be taught a sole `acompletion_with_retry` edge as the current live contract

#### Scenario: LLD observability is deeper than HTTP-only counters
- **WHEN** a reader opens the LLD observability flow
- **THEN** they find AI quality counters and/or feedback/tracing notes consistent with serving L3
- **AND** those signals are not described as the deploy gate

#### Scenario: LLD entities cover integrations and AI fields
- **WHEN** a reader opens the LLD data-model section
- **THEN** inbound/integration-related persistence is acknowledged
- **AND** thread title and note/file AI enrichment fields are not omitted as if absent

### Requirement: Residual keep-set laws match worker and AI observability hubs
`docs/documentation/rules.md` MUST document that the ARQ worker startup provides `ctx["arq_pool"]` for enqueue use (or an equivalent accurate law). The Observability section of `docs/documentation/ai.md` MUST name low-cardinality AI quality counters and optional feedback consistently with `system.md`, and MUST NOT present traces/thumbs as a production SLO.

#### Scenario: ARQ pool law matches worker startup
- **WHEN** a reader looks up ARQ enqueue rules in `rules.md`
- **THEN** they learn the worker context exposes a reusable pool on startup
- **AND** they are not told the pool is missing by default when startup sets it

#### Scenario: AI Observability footer matches the hub
- **WHEN** a reader opens the Observability section of `ai.md`
- **THEN** they find `dashnote_ai_*` (and feedback or equivalent serving signal) alongside HTTP metrics naming
- **AND** those signals are not called a production SLO
