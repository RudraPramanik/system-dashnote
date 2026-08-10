## 1. Soft AI health

- [x] 1.1 Add `GET /health/ai` on the health router (lazy Qdrant probe when `qdrant_enabled`; soft not-configured when disabled; never fold into hard `/health`)
- [x] 1.2 Confirm hard `GET /health` still only requires Postgres + Redis; Qdrant failure must not crash the API process

## 2. Production smoke script

- [x] 2.1 Create `scripts/smoke_prod.py` with `--base-url` / `SMOKE_BASE_URL` (default `http://127.0.0.1`), PASS/FAIL printing, exit 0/1
- [x] 2.2 Implement hard gate: `GET /health`, auth (ephemeral register or `SMOKE_EMAIL`/`SMOKE_PASSWORD` login), notebook + `POST /notes/`
- [x] 2.3 Add optional soft checks (default off): `GET /health/ai` and/or file upload poll via `--with-ai` / `SMOKE_SOFT_AI=1` — skip/warn only, never fail hard gate by default
- [x] 2.4 Reuse `httpx` patterns from `scripts/e2e_docker_smoke.py`; do not delete or replace that E2E script

## 3. Docs and tracker

- [x] 3.1 Add “Post-deploy smoke” section to `docs/deployment/runbook.md` (local + prod base URL, env vars, no secrets)
- [x] 3.2 Mark `docs/documentation/production.md` step 7P.6 as done with pointers to `smoke_prod.py` and `/health/ai`

## 4. Validate and close gate

- [x] 4.1 Against local stack: `python scripts/smoke_prod.py` (or `SMOKE_BASE_URL=http://127.0.0.1`) exits 0 on healthy compose
- [x] 4.2 Confirm hard `/health` unchanged when Qdrant is down; `/health/ai` reports soft status
- [x] 4.3 Confirm local `docker-compose.yml` and CI workflow were not required to change for this slice (touch only if smoke deps force it)
