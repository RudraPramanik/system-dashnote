## ADDED Requirements

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
