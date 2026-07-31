## Purpose

Remaining production platform behaviors (Slice 7P): R2/storage contract, deploy/runbook, smoke, soft AI health, CI/CD, and local Compose compatibility.

## Requirements

### Requirement: Production storage uses object store without shared volumes
When `STORAGE_BACKEND` is `r2` (or other S3-compatible remote), the worker MUST download file bytes via `get_storage().download(storage_key)` and MUST NOT depend on a shared filesystem volume with the API. Local development MAY continue using `STORAGE_BACKEND=local` with the Compose `local_storage` volume. Documentation MUST describe the R2 env contract in `.env.production.example` (or equivalent).

#### Scenario: Worker reads upload on R2-backed deploy
- **GIVEN** an uploaded file whose metadata exists in Postgres with a valid `storage_key`
- **AND** `STORAGE_BACKEND` is configured for remote object storage
- **WHEN** the automation worker processes the file upload event
- **THEN** the worker retrieves bytes through `get_storage().download(storage_key)`
- **AND** processing does not require a shared local volume between api and worker

#### Scenario: Local compose storage unchanged
- **GIVEN** local development with `STORAGE_BACKEND=local`
- **WHEN** operators run `docker compose up`
- **THEN** api and worker continue to share the documented local storage volume behavior

### Requirement: Deploy scripts and runbook exist
The repository MUST provide deploy helper scripts under `scripts/deploy/` and a runbook at `docs/deployment/runbook.md` covering migrate, start/update services, health verification, and rollback at a high level. Scripts MUST target the production compose profile (hosted data plane; thin VPS compute).

#### Scenario: Operator follows runbook after code update
- **GIVEN** a VPS with production compose and a filled `.env` for hosted services
- **WHEN** an operator follows `docs/deployment/runbook.md` and runs the deploy helpers
- **THEN** migrations can be applied and api/worker can be brought up or updated
- **AND** the runbook documents how to verify health and how to roll back a bad deploy

### Requirement: Production smoke script gates readiness
The system MUST provide `scripts/smoke_prod.py` (or equivalent) that, against a configurable base URL, verifies at least: health endpoint success, auth register/login, and note creation. Semantic search MAY be optional when AI/Qdrant are unavailable. A successful smoke run MUST exit 0; failure MUST exit non-zero.

#### Scenario: Smoke passes on healthy API
- **GIVEN** a reachable API with Postgres and Redis healthy
- **WHEN** an operator runs the smoke script with `SMOKE_BASE_URL` set to that API
- **THEN** the script exits 0 after health, auth, and note-create checks succeed

#### Scenario: Smoke fails when health is down
- **GIVEN** an API that returns non-success for the hard health check
- **WHEN** the smoke script runs against that base URL
- **THEN** the script exits non-zero

### Requirement: Soft AI health does not block hard health
`GET /health` MUST continue to treat Postgres and Redis as hard dependencies and MUST NOT fail solely because Qdrant or LLM providers are unavailable. If `GET /health/ai` is provided, it MUST report AI/Qdrant readiness as soft status and MUST NOT be required for the deploy smoke hard gate unless explicitly documented otherwise.

#### Scenario: API up while Qdrant is down
- **GIVEN** Postgres and Redis are reachable and Qdrant is unreachable
- **WHEN** a client calls `GET /health`
- **THEN** the response reflects hard-dependency health without requiring Qdrant success

### Requirement: CI runs on pull requests without production secrets
The repository MUST include a CI workflow that runs on pull requests (and pushes to the default branch as appropriate) executing pytest and a Docker image build. CI MUST NOT require production host credentials or live LLM/Qdrant secrets to pass.

#### Scenario: PR CI green without prod secrets
- **GIVEN** a pull request with passing unit/module tests
- **WHEN** CI executes
- **THEN** pytest and docker build complete successfully without production VPS or hosted-provider secrets

### Requirement: CD deploys main and runs smoke
A CD workflow MUST deploy from the default branch to the VPS (or documented target), run migrations as needed, update api/worker, and execute the production smoke script. Deploy MUST be considered failed if smoke exits non-zero.

#### Scenario: Merge to main triggers deploy and smoke
- **GIVEN** CD secrets and a configured VPS environment
- **WHEN** a change is merged to the default branch
- **THEN** the deploy workflow updates the running services
- **AND** runs the smoke script against the production base URL
- **AND** fails the workflow if smoke exits non-zero

### Requirement: Local compose remains the developer default
Changes for production platform MUST NOT break the documented local developer path: `docker compose up -d --build` followed by a successful hard health check at the documented local URL.

#### Scenario: Local stack still healthy after platform files land
- **GIVEN** the repository includes production compose, deploy scripts, and CI/CD workflows
- **WHEN** a developer runs the local full stack compose command
- **THEN** `GET /health` on the local edge URL succeeds for hard dependencies
