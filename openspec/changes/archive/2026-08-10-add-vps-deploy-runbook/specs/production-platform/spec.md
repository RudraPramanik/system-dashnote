## MODIFIED Requirements

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
