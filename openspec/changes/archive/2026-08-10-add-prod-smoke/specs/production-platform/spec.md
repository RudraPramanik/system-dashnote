## MODIFIED Requirements

### Requirement: Production smoke script gates readiness
The system MUST provide `scripts/smoke_prod.py` that, against a configurable base URL (`SMOKE_BASE_URL` or `--base-url`, default `http://127.0.0.1`), verifies at least: hard health success (`GET /health` with database reachable), auth register or login (`SMOKE_EMAIL` / `SMOKE_PASSWORD` when set; otherwise ephemeral register), and note creation (creating a notebook first when required by the API). Semantic search, file upload, worker automation polling, and `GET /health/ai` MAY run as soft/optional checks and MUST NOT cause a hard failure unless explicitly documented as required. A successful hard-gate run MUST exit 0; any hard-gate failure MUST exit non-zero. `docs/deployment/runbook.md` MUST document the post-deploy smoke command and env vars. When this deliverable is complete, `docs/documentation/production.md` MUST mark step 7P.6 as done. The broader `scripts/e2e_docker_smoke.py` MAY remain as a local E2E and MUST NOT be required as the CD hard gate.

#### Scenario: Smoke passes on healthy API
- **GIVEN** a reachable API with Postgres and Redis healthy
- **WHEN** an operator runs `scripts/smoke_prod.py` with `SMOKE_BASE_URL` set to that API
- **THEN** the script exits 0 after health, auth, and note-create hard checks succeed

#### Scenario: Smoke fails when health is down
- **GIVEN** an API that returns non-success for the hard health check
- **WHEN** the smoke script runs against that base URL
- **THEN** the script exits non-zero

#### Scenario: Soft AI checks do not fail the hard gate by default
- **GIVEN** a healthy API where Qdrant or LLM is unavailable
- **WHEN** the operator runs the default hard-gate smoke (soft AI not required)
- **THEN** the script still exits 0 if health, auth, and note create succeed
- **AND** any soft AI/file steps are reported as skip/warn rather than hard fail

#### Scenario: Runbook documents post-deploy smoke
- **GIVEN** Slice 7P.6 is complete
- **WHEN** an operator opens `docs/deployment/runbook.md`
- **THEN** a post-deploy smoke section documents how to run `scripts/smoke_prod.py` against local and production base URLs
- **AND** documents optional credential env vars without embedding secrets

#### Scenario: Tracker updated when smoke closes
- **GIVEN** `scripts/smoke_prod.py`, soft AI health behavior, and runbook smoke docs are in place
- **WHEN** the implementer closes Slice 7P.6
- **THEN** `docs/documentation/production.md` shows 7P.6 as complete

### Requirement: Soft AI health does not block hard health
`GET /health` MUST continue to treat Postgres and Redis as hard dependencies and MUST NOT fail solely because Qdrant or LLM providers are unavailable. The system MUST provide `GET /health/ai` that reports AI/Qdrant readiness as soft status (reachable, degraded, or not configured). `GET /health/ai` MUST NOT be required for the deploy smoke hard gate unless an operator explicitly opts into soft checks. Soft Qdrant probe failures MUST NOT crash the API process.

#### Scenario: API up while Qdrant is down
- **GIVEN** Postgres and Redis are reachable and Qdrant is unreachable
- **WHEN** a client calls `GET /health`
- **THEN** the response reflects hard-dependency health without requiring Qdrant success

#### Scenario: Soft AI health endpoint reports Qdrant separately
- **GIVEN** the API is running with `QDRANT_URL` configured
- **WHEN** a client calls `GET /health/ai`
- **THEN** the response reports Qdrant readiness as soft status
- **AND** a Qdrant outage does not change the hard success criteria of `GET /health`

#### Scenario: Soft AI health when Qdrant is not configured
- **GIVEN** the API is running without `QDRANT_URL`
- **WHEN** a client calls `GET /health/ai`
- **THEN** the response indicates AI/Qdrant is not configured (soft)
- **AND** `GET /health` remains independent of that result
