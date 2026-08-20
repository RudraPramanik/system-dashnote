## Why

On the deploy-first path, 7P.0–7P.4 and thin CI (7P.7) are done; the next platform gate is a repeatable manual VPS deploy path (7P.5). Operators need a runbook and shell helpers that target `docker-compose.prod.yml` before smoke (7P.6) and CD (7P.8) can rely on a documented sequence.

## What Changes

- Add `docs/deployment/runbook.md` covering prerequisites, first-time VPS setup, release deploy sequence, rollback, TLS options, and optional observability profile
- Add bash deploy helpers under `scripts/deploy/`: `migrate.sh`, `up.sh`, `health-check.sh` (LF endings; documented `chmod +x`)
- Scripts MUST use `docker compose -f docker-compose.prod.yml` and MUST NOT embed secrets (read `.env` on the VPS)
- Mark `docs/documentation/production.md` step 7P.5 as done
- Do **not** implement smoke (`scripts/smoke_prod.py` / 7P.6), CD (`deploy.yml` / 7P.8), TLS termination itself, or change local `docker-compose.yml`

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Tighten the deploy-scripts/runbook requirement to the concrete 7P.5 deliverables (`docs/deployment/runbook.md`, `scripts/deploy/{migrate,up,health-check}.sh`), compose-file targeting, no-secrets-in-scripts law, TLS decision documentation, and closing the tracker when 7P.5 is done.

## Impact

- Docs: new `docs/deployment/runbook.md`; tracker update in `production.md`
- Scripts: new `scripts/deploy/*.sh` for Linux VPS operators (PowerShell notes only in the runbook for local Windows)
- Compose: no structural change expected; validate with `docker compose -f docker-compose.prod.yml config`
- Out of scope: real VPS provisioning, TLS cert install, smoke script (7P.6), CD workflow (7P.8), evals/HITL
