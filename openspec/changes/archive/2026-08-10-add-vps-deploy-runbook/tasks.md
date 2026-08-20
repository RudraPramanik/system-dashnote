## 1. Runbook

- [x] 1.1 Create `docs/deployment/runbook.md` with prerequisites (Ubuntu 22.04+, Docker Compose plugin, hosted Postgres/Redis/Qdrant/R2, DNS)
- [x] 1.2 Document first-time VPS setup: clone/copy compose files, `cp .env.production.example .env`, fill secrets, `docker compose -f docker-compose.prod.yml build`
- [x] 1.3 Document every-release sequence (`migrate.sh` → `up.sh` → `health-check.sh`), rollback, TLS options (Cloudflare / Caddy / Certbot), and optional `--profile observability`
- [x] 1.4 Add brief PowerShell / Windows notes for local operators (scripts themselves remain bash for VPS)

## 2. Deploy scripts

- [x] 2.1 Add `scripts/deploy/migrate.sh` (`set -euo pipefail`; `docker compose -f docker-compose.prod.yml run --rm migrate`; no secrets)
- [x] 2.2 Add `scripts/deploy/up.sh` (bring up api, wait for health, then worker + nginx; optional observability note)
- [x] 2.3 Add `scripts/deploy/health-check.sh` (`curl -sf http://127.0.0.1/health`; exit non-zero if not ok; graceful without `jq` if needed)
- [x] 2.4 Ensure LF line endings (`.gitattributes` for `scripts/deploy/*.sh` if helpful) and document `chmod +x scripts/deploy/*.sh` in the runbook

## 3. Validate and close gate

- [x] 3.1 Run `docker compose -f docker-compose.prod.yml config` and confirm it parses (no need for a live VPS in this change)
- [x] 3.2 Confirm scripts contain no hard-coded secrets and always use `-f docker-compose.prod.yml`
- [x] 3.3 Confirm local `docker-compose.yml` was not modified
- [x] 3.4 Mark `docs/documentation/production.md` step 7P.5 as done
