## ADDED Requirements

### Requirement: Production API is served at the aisystem HTTPS hostname
Operators MUST publish the production API at `https://api.aisystem.world` using DNS that targets the thin VPS public address and browser TLS via Cloudflare. Origin nginx MUST serve HTTPS on port 443 with a certificate acceptable to Cloudflare **Full** (self-signed MAY be used; Full strict MUST NOT be required for this change). Port 80 MAY remain open. `GET https://api.aisystem.world/health` MUST return success, and `scripts/smoke_prod.py` with `SMOKE_BASE_URL=https://api.aisystem.world` MUST exit 0 before A7 / production-live MAY be claimed. HTTP-on-IP first-boot evidence MUST remain distinct and MUST NOT alone close A7.

#### Scenario: HTTPS health on api hostname
- **GIVEN** Cloudflare DNS for `api.aisystem.world` points at the VPS and SSL mode is Full with origin `:443` reachable
- **WHEN** an operator requests `GET https://api.aisystem.world/health`
- **THEN** the response indicates hard health success
- **AND** the claim for A7 MAY proceed only together with HTTPS smoke exit 0

#### Scenario: HTTPS smoke closes A7
- **GIVEN** HTTPS health on `api.aisystem.world` succeeds
- **WHEN** an operator runs `scripts/smoke_prod.py` with `SMOKE_BASE_URL=https://api.aisystem.world` and the script exits 0
- **THEN** A7 / production-live MAY be recorded
- **AND** `docs/devops-progress.md` and the A-gate in `docs/documentation/blueprint/goal.md` MUST be updated together

### Requirement: Production CORS names the apex frontend origin
The VPS production env MUST set `CORS_ORIGINS` to include `https://aisystem.world` and MUST NOT use `*`. Localhost origins MAY remain listed for developer browsers. Changing CORS MUST be followed by restarting or redeploying the API process so the new origins take effect. This change MUST NOT require the frontend to be hosted on the VPS.

#### Scenario: CORS rejects wildcard in production
- **GIVEN** the production `.env` on the VPS after this change
- **WHEN** an operator inspects `CORS_ORIGINS`
- **THEN** the value does not contain `*`
- **AND** `https://aisystem.world` is listed

#### Scenario: Frontend stays off the API VPS
- **GIVEN** the thin VPS production compose
- **WHEN** operators review where the product UI runs
- **THEN** documentation states the VPS runs api and worker (and nginx) only
- **AND** the apex frontend is not required to run on that same VPS

### Requirement: Live edge ownership is documented
The repository MUST document which layer owns DNS/TLS (Cloudflare), compute and security group (AWS / Terraform), and app processes (Docker Compose on the VPS). Operators MUST be instructed to SSH to the VPS by public IP, not via the Cloudflare-proxied API hostname.

#### Scenario: Operator finds the ownership map
- **GIVEN** the deployment docs after this change
- **WHEN** an operator opens the runbook or edge doc for `aisystem.world`
- **THEN** Cloudflare, Terraform/EC2, and Compose responsibilities are distinguished
- **AND** SSH-via-proxied-hostname is discouraged

### Requirement: CD smoke targets the HTTPS API hostname
When GitHub CD is configured for production, `SMOKE_BASE_URL` MUST be `https://api.aisystem.world` (not the HTTP IP) for production-live gates. SSH deploy MAY continue to use the VPS public IP. This change MUST NOT require frontend deployment for a CD hard gate.

#### Scenario: CD secret uses HTTPS API URL
- **GIVEN** an operator configures deploy workflow secrets after A7
- **WHEN** they set `SMOKE_BASE_URL`
- **THEN** the value is `https://api.aisystem.world`
- **AND** the hard gate remains health, auth, and note create via `scripts/smoke_prod.py`

## MODIFIED Requirements

### Requirement: Deploy scripts and runbook exist
The repository MUST provide deploy helper scripts at `scripts/deploy/migrate.sh`, `scripts/deploy/up.sh`, and `scripts/deploy/health-check.sh`, plus an operator runbook at `docs/deployment/runbook.md`. Scripts MUST invoke `docker compose -f docker-compose.prod.yml` (hosted data plane; thin VPS compute), MUST use `set -euo pipefail` (or equivalent fail-fast), and MUST NOT embed secrets (credentials come from the VPS `.env` / compose `env_file`). The runbook MUST cover: prerequisites checklist, first-time VPS setup, every-release deploy sequence (migrate → up → health-check), rollback, TLS options (Cloudflare / Caddy / Certbot), and optional observability profile usage. For `aisystem.world`, the runbook MUST document the chosen Cloudflare **Full** + origin `:443` path for `api.aisystem.world` (DNS A record, proxied, self-signed origin cert OK for Full) and the HTTPS smoke commands that close A7. `health-check.sh` MUST verify hard health at the published edge (`http://127.0.0.1/health`) and exit non-zero on failure. When this deliverable is complete, `docs/documentation/production.md` MUST mark step 7P.5 as done.

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
- **AND** Caddy and Certbot remain optional paths that this change does not require to be implemented on the VPS

#### Scenario: Runbook documents TLS options and the chosen aisystem path
- **GIVEN** Slice 7P.5 is complete and this domain change is applied
- **WHEN** an operator opens the TLS section of `docs/deployment/runbook.md`
- **THEN** at least Cloudflare SSL, Caddy, and Certbot+nginx are listed as options
- **AND** the Cloudflare Full + origin `:443` path for `api.aisystem.world` is documented as the current production choice for A7
- **AND** HTTPS smoke against `https://api.aisystem.world` is documented

#### Scenario: Tracker updated when deploy runbook closes
- **GIVEN** runbook and deploy scripts are in place
- **WHEN** the implementer closes Slice 7P.5
- **THEN** `docs/documentation/production.md` shows 7P.5 as complete
