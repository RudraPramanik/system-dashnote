## MODIFIED Requirements

### Requirement: System doc lists the mounted HTTP surface
`docs/documentation/system.md` MUST describe every router prefix registered by the API entrypoint, including health, auth, workspaces, membership, notebooks, notes, files, integrations, and AI (chat, threads, agent, diagnostic search, feedback). It MUST include HITL agent routes (`POST /ai/agent/resume`, `POST /ai/agent/reject`), `POST /ai/feedback`, and `GET /health/ai` as the soft AI probe. It MUST NOT list an unmounted diagnostic search method as the live contract.

#### Scenario: Reader finds integrations and HITL on the router table
- **GIVEN** the API registers `/integrations` and agent resume/reject
- **WHEN** a reader opens `docs/documentation/system.md`
- **THEN** those prefixes and routes appear in the routing overview
- **AND** inbound email / WhatsApp are not omitted as if they were out of tree

#### Scenario: Soft health is documented without becoming the deploy gate
- **WHEN** a reader looks up health in `system.md`
- **THEN** `GET /health` remains the hard Postgres + Redis gate
- **AND** `GET /health/ai` is documented as a soft Qdrant/LLM probe that MUST NOT fail the hard gate

#### Scenario: Reader finds feedback on the router table
- **GIVEN** the API registers `POST /ai/feedback`
- **WHEN** a reader opens `docs/documentation/system.md`
- **THEN** that route appears in the routing overview
- **AND** workspace identity for feedback is documented as JWT `wid` only

### Requirement: AI doc describes live agent and search contracts
`docs/documentation/ai.md` MUST document the live diagnostic search as `GET /ai/test-search`, the coexisting chat and agent surfaces, HITL `approval_required` plus resume/reject, `POST /ai/feedback`, and soft `GET /health/ai`. Fast RAG (`/ai/chat*`) and the agent (`/ai/agent*`) MUST remain documented as separate paths.

#### Scenario: Agent HITL is in the AI contract doc
- **WHEN** a reader implements or calls the agent from `ai.md`
- **THEN** they find `POST /ai/agent`, `POST /ai/agent/stream`, `POST /ai/agent/resume`, and `POST /ai/agent/reject`
- **AND** they find that mutation tools pause for approval rather than auto-committing

#### Scenario: Diagnostic search method matches the mounted route
- **WHEN** a reader looks up `/ai/test-search` in `ai.md`
- **THEN** the documented method is GET with query `q` and `limit`
- **AND** the doc MUST NOT present unmounted POST `/ai/test-search` as the live validation endpoint

#### Scenario: Feedback is in the AI contract doc
- **WHEN** a reader looks up AI HTTP surfaces in `ai.md`
- **THEN** they find `POST /ai/feedback`
- **AND** they find that chat and agent turns MUST NOT require a feedback call to complete

## ADDED Requirements

### Requirement: System observability matches serving L3 without becoming a gate
`docs/documentation/system.md` MUST document Prometheus `/metrics` as both HTTP instrumentation (`dashnote_api_*`) and low-cardinality AI quality counters (`dashnote_ai_*`). It MUST point readers at the eval lifecycle (`evals/BLUEPRINT.md` or `evals/README.md`) with L0–L3 marked implemented. Traces, thumbs, and quality counters MUST NOT be described as the hard deploy gate or as a production SLO. `evals/BLUEPRINT.md` MUST NOT still label L3 as the current unimplemented phase.

#### Scenario: Metrics series are both named
- **WHEN** a reader looks up metrics in `system.md`
- **THEN** they find `GET /metrics` with `dashnote_api_*` and `dashnote_ai_*`
- **AND** they are told those series are not a production SLO

#### Scenario: Eval map agrees with the system hub
- **WHEN** a reader follows the eval pointer from `system.md`
- **THEN** L3 production observability is documented as implemented serving traces, feedback, and Prometheus counters
- **AND** L3 is not described as an open implementation phase

### Requirement: Sibling keep-set docs do not contradict the system map
Canonical keep-set docs that copy the mounted HTTP surface (`ai.md`, `lld.md`, `openspec/config.yaml`, and the README live-surface list when it enumerates `/ai` routes) MUST NOT omit `POST /ai/feedback` or describe Grafana as a default local Compose service. They MUST NOT claim HTTPS production-live or a production-grade startup / mid-enterprise product while A7 remains open. This requirement MUST NOT delete files owned by `consolidate-docs`.

#### Scenario: LLD composition matches the hub
- **WHEN** a reader opens the composition section of `docs/documentation/lld.md`
- **THEN** they find `POST /ai/feedback` among mounted AI routes or an explicit pointer to the `system.md` router table that includes it
- **AND** metrics mention both `dashnote_api_*` and `dashnote_ai_*`

#### Scenario: OpenSpec context lists feedback
- **WHEN** an agent reads `openspec/config.yaml` HTTP surface
- **THEN** `POST /ai/feedback` is listed with the other `/ai` routes
- **AND** tenancy for that route remains JWT `wid` only
