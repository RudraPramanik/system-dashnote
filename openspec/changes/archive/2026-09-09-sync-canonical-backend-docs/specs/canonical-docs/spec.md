## Purpose

Canonical architecture docs under `docs/documentation/` are the in-repo contract for routing, AI, health, and local Compose. They must match the mounted API and working file paths so humans and agents do not follow dead `src/docs/` links or missing routers.

## ADDED Requirements

### Requirement: System doc lists the mounted HTTP surface
`docs/documentation/system.md` MUST describe every router prefix registered by the API entrypoint, including health, auth, workspaces, membership, notebooks, notes, files, integrations, and AI (chat, threads, agent, diagnostic search). It MUST include HITL agent routes (`POST /ai/agent/resume`, `POST /ai/agent/reject`) and `GET /health/ai` as the soft AI probe. It MUST NOT list an unmounted diagnostic search method as the live contract.

#### Scenario: Reader finds integrations and HITL on the router table
- **GIVEN** the API registers `/integrations` and agent resume/reject
- **WHEN** a reader opens `docs/documentation/system.md`
- **THEN** those prefixes and routes appear in the routing overview
- **AND** inbound email / WhatsApp are not omitted as if they were out of tree

#### Scenario: Soft health is documented without becoming the deploy gate
- **WHEN** a reader looks up health in `system.md`
- **THEN** `GET /health` remains the hard Postgres + Redis gate
- **AND** `GET /health/ai` is documented as a soft Qdrant/LLM probe that MUST NOT fail the hard gate

### Requirement: Canonical docs use working documentation paths
Canonical docs (`system.md`, `ai.md`, `lld.md`, `observe.md`) MUST link related architecture files under `docs/documentation/` (and `docs/observability.md` where that runbook is the human guide). They MUST NOT send readers to `src/docs/` as if those files still exist.

#### Scenario: Cross-links resolve in-repo
- **WHEN** a reader follows related-doc links from `system.md` or `ai.md`
- **THEN** each link targets an existing path under `docs/`
- **AND** no canonical related-doc table lists `src/docs/system.md` or `src/docs/ai.md` as current locations

### Requirement: System and observe docs match local Compose
`system.md` and observability docs MUST list local Compose services that currently run from `docker-compose.yml`. Prometheus MAY be listed. Grafana MUST NOT be described as a default local Compose service on port 3001 unless that service is restored in compose.

#### Scenario: Local stack list matches compose
- **GIVEN** `docker-compose.yml` starts nginx, api, db, redis, worker, qdrant, prometheus, and migrate, and does not start grafana
- **WHEN** a reader follows the local Compose section
- **THEN** they can start the documented services without expecting a Grafana UI on `:3001` as part of `docker compose up`

### Requirement: AI doc describes live agent and search contracts
`docs/documentation/ai.md` MUST document the live diagnostic search as `GET /ai/test-search`, the coexisting chat and agent surfaces, HITL `approval_required` plus resume/reject, and soft `GET /health/ai`. Fast RAG (`/ai/chat*`) and the agent (`/ai/agent*`) MUST remain documented as separate paths.

#### Scenario: Agent HITL is in the AI contract doc
- **WHEN** a reader implements or calls the agent from `ai.md`
- **THEN** they find `POST /ai/agent`, `POST /ai/agent/stream`, `POST /ai/agent/resume`, and `POST /ai/agent/reject`
- **AND** they find that mutation tools pause for approval rather than auto-committing

#### Scenario: Diagnostic search method matches the mounted route
- **WHEN** a reader looks up `/ai/test-search` in `ai.md`
- **THEN** the documented method is GET with query `q` and `limit`
- **AND** the doc MUST NOT present unmounted POST `/ai/test-search` as the live validation endpoint
