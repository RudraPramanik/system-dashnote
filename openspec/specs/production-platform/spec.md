## Purpose

Remaining production platform behaviors (Slice 7P): R2/storage contract, deploy/runbook, smoke, soft AI health, CI/CD, and local Compose compatibility.

## Requirements

### Requirement: Production storage uses object store without shared volumes
When `STORAGE_BACKEND` is `r2` (or other S3-compatible remote), the worker MUST download file bytes via `get_storage().download(storage_key)` and MUST NOT depend on a shared filesystem volume with the API. Local development MAY continue using `STORAGE_BACKEND=local` with the Compose `local_storage` volume. Documentation MUST describe the R2 env contract in `.env.production.example` and MUST provide an operator-facing storage contract at `docs/deployment/storage.md` covering why prod needs object storage, the env checklist, and a clear local-dev vs prod comparison. API file upload and worker automation download paths MUST use `get_storage()` (no direct `LOCAL_STORAGE_PATH` filesystem reads for file bytes). When this contract is complete, `docs/documentation/production.md` MUST mark step 7P.4 as done.

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

#### Scenario: Operator reads storage contract doc
- **GIVEN** Slice 7P.4 is complete
- **WHEN** an operator opens `docs/deployment/storage.md`
- **THEN** the doc explains why prod uses R2/S3-compatible storage (no shared api/worker volume)
- **AND** lists the required env vars (`STORAGE_BACKEND`, `R2_*` or equivalent)
- **AND** contrasts local `STORAGE_BACKEND=local` with prod `STORAGE_BACKEND=r2`

#### Scenario: Tracker updated when storage contract closes
- **GIVEN** storage contract documentation is in place and api/worker use `get_storage()` for file bytes
- **WHEN** the implementer closes Slice 7P.4
- **THEN** `docs/documentation/production.md` shows 7P.4 as complete

### Requirement: Deploy scripts and runbook exist
The repository MUST provide deploy helper scripts at `scripts/deploy/migrate.sh`, `scripts/deploy/up.sh`, and `scripts/deploy/health-check.sh`, plus an operator runbook at `docs/deployment/runbook.md`. Scripts MUST invoke `docker compose -f docker-compose.prod.yml` (hosted data plane; thin VPS compute), MUST use `set -euo pipefail` (or equivalent fail-fast), and MUST NOT embed secrets (credentials come from the VPS `.env` / compose `env_file`). The runbook MUST cover: prerequisites checklist, first-time VPS setup, every-release deploy sequence (migrate → up → health-check), rollback, TLS options as a decision (Cloudflare / Caddy / Certbot — documentation only), and optional observability profile usage. `health-check.sh` MUST verify hard health at the published edge (`http://127.0.0.1/health`) and exit non-zero on failure. When this deliverable is complete, `docs/documentation/production.md` MUST mark step 7P.5 as done.

#### Scenario: Operator follows runbook after code update
- **GIVEN** a VPS with production compose files and a filled `.env` for hosted services
- **WHEN** an operator follows `docs/deployment/runbook.md` and runs the deploy helpers
- **THEN** migrations can be applied via `migrate.sh`
- **AND** api/worker/nginx can be brought up or updated via `up.sh`
- **AND** `health-check.sh` verifies hard health at the edge URL
- **AND** the runbook documents how to roll back a bad deploy

#### Scenario: Scripts never embed secrets
- **GIVEN** the contents of `scripts/deploy/*.sh`
- **WHEN** an operator reviews them before running on a VPS
- **THEN** no production passwords, API keys, or connection strings are hard-coded
- **AND** compose is invoked with `-f docker-compose.prod.yml` so local full-stack compose is not used by accident

#### Scenario: Runbook documents TLS options without implementing them
- **GIVEN** Slice 7P.5 is complete
- **WHEN** an operator opens the TLS section of `docs/deployment/runbook.md`
- **THEN** at least Cloudflare SSL, Caddy, and Certbot+nginx are listed as options
- **AND** the section does not require a specific TLS implementation to be shipped in this change

#### Scenario: Tracker updated when deploy runbook closes
- **GIVEN** runbook and deploy scripts are in place
- **WHEN** the implementer closes Slice 7P.5
- **THEN** `docs/documentation/production.md` shows 7P.5 as complete

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
`GET /health` MUST continue to treat Postgres and Redis as hard dependencies and MUST NOT fail solely because Qdrant or LLM providers are unavailable. The system MUST provide `GET /health/ai` that reports AI/Qdrant readiness as soft status (reachable, degraded, or not configured) **and** a soft LLM dependency (reachable, degraded, or not configured). `GET /health/ai` MUST NOT be required for the deploy smoke hard gate unless an operator explicitly opts into soft checks. Soft Qdrant or LLM probe failures MUST NOT crash the API process.

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

#### Scenario: Soft AI health reports LLM separately
- **GIVEN** the API is running with at least one LLM candidate configured
- **WHEN** a client calls `GET /health/ai`
- **THEN** the response includes a soft LLM dependency status
- **AND** a retired or unreachable LLM does not change the hard success criteria of `GET /health`

### Requirement: CI runs on pull requests without production secrets
The repository MUST include a CI workflow that runs on pull requests (and pushes to the default branch as appropriate) executing pytest and a Docker image build. CI MUST NOT require production host credentials or live LLM/Qdrant secrets to pass.

#### Scenario: PR CI green without prod secrets
- **GIVEN** a pull request with passing unit/module tests
- **WHEN** CI executes
- **THEN** pytest and docker build complete successfully without production VPS or hosted-provider secrets

### Requirement: CD deploys main and runs smoke
A CD workflow MUST exist at `.github/workflows/deploy.yml` and MUST deploy to the configured VPS (or documented target) only on `workflow_dispatch` and on pushes of version tags matching `v*` — it MUST NOT auto-deploy on every push or merge to the default branch. The workflow MUST build and push the application image to GHCR (or the documented registry), set the VPS `IMAGE` (or equivalent compose image override already used by `docker-compose.prod.yml`) to that tag, run migrations as needed, update api/worker (and documented edge services), and execute hard health verification plus `scripts/smoke_prod.py`. Deploy MUST be considered failed if health-check or smoke exits non-zero. `docs/deployment/runbook.md` MUST document required GitHub Secrets, trigger rules, and a production gate checklist. When this deliverable is complete, `docs/documentation/production.md` MUST mark step 7P.8 as done.

#### Scenario: Tag or manual dispatch triggers deploy and smoke
- **GIVEN** CD secrets and a configured VPS environment
- **WHEN** an operator pushes a `v*` tag or runs `workflow_dispatch`
- **THEN** the deploy workflow builds and pushes an image to the documented registry
- **AND** updates running services on the VPS (migrate then up, using existing deploy helpers or equivalent)
- **AND** runs hard health verification
- **AND** runs `scripts/smoke_prod.py` against the configured production base URL
- **AND** fails the workflow if health-check or smoke exits non-zero

#### Scenario: Merge to default branch does not auto-deploy
- **GIVEN** CD is configured
- **WHEN** a change is merged or pushed to the default branch without a `v*` tag and without `workflow_dispatch`
- **THEN** the deploy workflow does not run solely because of that merge/push

#### Scenario: Scripts and secrets stay out of the workflow files
- **GIVEN** the contents of `.github/workflows/deploy.yml`
- **WHEN** an operator reviews the workflow before enabling secrets
- **THEN** no production passwords, API keys, or connection strings are hard-coded
- **AND** VPS host credentials and smoke base URL come from GitHub Secrets (or documented vars)

#### Scenario: Runbook documents CD secrets and production gate
- **GIVEN** Slice 7P.8 is complete
- **WHEN** an operator opens `docs/deployment/runbook.md`
- **THEN** a GitHub Secrets / CD section lists required secrets and trigger rules (`v*` / `workflow_dispatch`)
- **AND** a production gate checklist includes hard health and smoke success before claiming production-live

#### Scenario: Tracker updated when CD gate closes
- **GIVEN** `deploy.yml`, compose image override compatibility, and runbook CD/gate docs are in place
- **WHEN** the implementer closes Slice 7P.8
- **THEN** `docs/documentation/production.md` shows 7P.8 as complete

### Requirement: Prod compose accepts registry image without rebuild
`docker-compose.prod.yml` MUST allow api, worker, and migrate to run from a registry image via the existing `IMAGE` environment variable (defaulting to a local tag when unset) so a CD deploy can `docker pull` and start services without requiring an on-VPS source rebuild. Local developer compose (`docker-compose.yml`) MUST remain the default path and MUST NOT be required to change for this behavior.

#### Scenario: VPS pulls CD image via IMAGE
- **GIVEN** `IMAGE` is set to a GHCR (or documented registry) tag on the VPS
- **WHEN** an operator runs prod compose up (directly or via deploy helpers)
- **THEN** api/worker/migrate use that image
- **AND** a full on-server `docker build` is not required for that release

#### Scenario: Unset IMAGE still allows local prod compose build
- **GIVEN** `IMAGE` is unset
- **WHEN** an operator runs `docker compose -f docker-compose.prod.yml` with build available
- **THEN** services can still build from the local Dockerfile as today

### Requirement: Local compose remains the developer default
Changes for production platform MUST NOT break the documented local developer path: `docker compose up -d --build` followed by a successful hard health check at the documented local URL.

#### Scenario: Local stack still healthy after platform files land
- **GIVEN** the repository includes production compose, deploy scripts, and CI/CD workflows
- **WHEN** a developer runs the local full stack compose command
- **THEN** `GET /health` on the local edge URL succeeds for hard dependencies

### Requirement: First-boot HTTP-on-IP is distinct from production-live
Operators MUST be able to first-boot the production compose stack on a thin VPS and prove hard health plus `scripts/smoke_prod.py` against `http://<vps-public-ip>` (or equivalent HTTP edge URL) when no domain or TLS certificate exists. Successful HTTP-on-IP health and smoke MUST be recordable as first-boot evidence. Operators MUST NOT treat that evidence as A7 TLS, HTTPS A4, production-live, or hire-ready. GitHub CD HTTPS smoke MUST NOT be required to close first-boot.

#### Scenario: HTTP smoke on public IP closes first-boot only
- **GIVEN** hosted Postgres and Redis are reachable from the VPS
- **AND** production compose is running api, worker, and nginx
- **AND** no domain or TLS is configured
- **WHEN** an operator runs `GET http://<vps-public-ip>/health` successfully
- **AND** runs `scripts/smoke_prod.py` with `SMOKE_BASE_URL` set to that HTTP URL and the script exits 0
- **THEN** first-boot MAY be recorded as proven
- **AND** A7 / production-live / job-search claims MUST remain false

#### Scenario: Missing domain does not block first-boot
- **GIVEN** hosted data-plane credentials exist and SSH to the VPS works
- **AND** no `api.<domain>` DNS record exists
- **WHEN** the operator follows the first-boot runbook path
- **THEN** they are instructed to smoke over HTTP on the public IP
- **AND** they are not required to obtain a certificate or domain in this change

#### Scenario: HTTPS production-live remains a later gate
- **GIVEN** HTTP-on-IP first-boot smoke has passed
- **WHEN** an operator reviews whether production-live may be claimed
- **THEN** the claim MUST remain false until `GET https://<prod-api>/health` succeeds and HTTPS `smoke_prod.py` exits 0

### Requirement: Thin VPS first-boot keeps data plane hosted
On a VPS with approximately 2 GB RAM, first-boot MUST run only the thin production compose path (api, worker, nginx). Postgres, Redis, Qdrant, and object storage MUST remain hosted services reached via env URLs. Operators MUST NOT start the local full-stack compose file on the VPS. Optional Prometheus/observability profile MUST stay off for first-boot. Sibling frontend MUST NOT be required to run on the same VPS.

#### Scenario: Prod compose has no in-box database
- **GIVEN** an operator first-boots the documented production compose file
- **WHEN** they inspect running services
- **THEN** api, worker, and nginx are the expected app/edge processes
- **AND** Postgres, Redis, and Qdrant are not started as local compose services on that VPS

#### Scenario: Full local compose is forbidden on the VPS
- **GIVEN** the first-boot runbook
- **WHEN** an operator reads how to start production
- **THEN** they are told to use `docker-compose.prod.yml` only
- **AND** they are told not to run the local full-stack `docker-compose.yml` on the VPS

#### Scenario: Observability profile stays off first boot
- **GIVEN** a 2 GB RAM VPS
- **WHEN** first-boot starts
- **THEN** the optional Prometheus/observability profile is not required
- **AND** docs state it MUST remain disabled until RAM headroom is proven

### Requirement: Gitignored production env is the VPS secret path
Operators MUST fill a gitignored production env file from `.env.production.example` and copy it to the VPS as compose `env_file` (`.env`). The example template MUST remain the committed contract. Filled production env files MUST NOT be committed. First-boot CORS MUST NOT use `*` even when the public URL is an HTTP IP.

#### Scenario: Example stays in git, secrets stay out
- **GIVEN** an operator prepares VPS credentials
- **WHEN** they create a filled production env from `.env.production.example`
- **THEN** that filled file is gitignored
- **AND** `.env.production.example` remains the committed template without live secrets

#### Scenario: VPS compose reads copied env
- **GIVEN** a filled production env on the operator machine
- **WHEN** they complete first-boot setup
- **THEN** the VPS compose `env_file` contains hosted `DATABASE_URL`, `REDIS_URL`, storage, and JWT settings
- **AND** deploy scripts still do not embed those secrets

#### Scenario: CORS stays explicit on HTTP first-boot
- **GIVEN** no production frontend domain exists yet
- **WHEN** first-boot env is written
- **THEN** `CORS_ORIGINS` MUST NOT be `*`
- **AND** local frontend origins MAY remain listed until a TLS app origin exists
