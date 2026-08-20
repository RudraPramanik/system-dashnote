## 1. Production storage contract (7P.4)

- [ ] 1.1 Document R2/S3 env vars and worker download contract in `.env.production.example` (and cross-link from `production.md`)
- [ ] 1.2 Verify `get_storage().download(storage_key)` path for remote backend; confirm local `STORAGE_BACKEND=local` + Compose volume behavior unchanged
- [ ] 1.3 Mark 7P.4 done in `docs/documentation/production.md` step checklist

## 2. Deploy scripts and runbook (7P.5)

- [ ] 2.1 Add `scripts/deploy/` helpers (migrate, up/update, health-check) for `docker-compose.prod.yml`
- [ ] 2.2 Write `docs/deployment/runbook.md` (deploy, verify, rollback, LLM/Qdrant soft-down notes)
- [ ] 2.3 Mark 7P.5 done in `production.md`

## 3. Health and smoke (7P.6) — API path

- [ ] 3.1 Add optional `GET /health/ai` soft probe (Qdrant / `ai_enabled`); keep `GET /health` hard deps = Postgres + Redis only
- [ ] 3.2 Implement `scripts/smoke_prod.py` (health, auth register/login, create note; optional `/ai/test-search`)
- [ ] 3.3 Extend `scripts/e2e_agent_test.py` to accept configurable base URL for prod runs
- [ ] 3.4 Add focused pytest for hard vs soft health behavior under `tests/`
- [ ] 3.5 Mark 7P.6 done in `production.md`

## 4. CI and CD (7P.7–7P.8)

- [ ] 4.1 Add `.github/workflows/ci.yml` — pytest + docker build on PR/main; no production secrets
- [ ] 4.2 Add `.github/workflows/deploy.yml` — build/push, SSH deploy, migrate, smoke; fail on smoke non-zero
- [ ] 4.3 Document required GitHub/VPS secrets in runbook; update `production.md` for 7P.7–7P.8 (pending real VPS gate if credentials absent)
- [ ] 4.4 Confirm local `docker compose up -d --build` + `/health` still pass after platform files land

## 5. AI eval harness

- [ ] 5.1 Create `evals/golden/` with ≥10 JSONL cases (retrieval + tenant isolation themes)
- [ ] 5.2 Implement `evals/run_eval.py` CLI (`--base-url`, `--token`) with PASS X/Y summary and failing case ids
- [ ] 5.3 Implement tenant-isolation case: member JWT must not retrieve peer private note via search/RAG; workspace from JWT only
- [ ] 5.4 Add `evals/README.md` with how to run locally and against a deployed API
- [ ] 5.5 Add unit tests where practical (e.g. `build_rbac_filter` member vs admin) under `tests/ai/`

## 6. Portfolio baseline docs

- [ ] 6.1 Rewrite root `readme.md`: pitch, stack, architecture links, built capabilities table, live URL placeholders
- [ ] 6.2 Add eval pass-rate and cost/latency fields (filled or explicitly pending); no unverified “production-ready” claims
- [ ] 6.3 Cross-link `goal.md` / `ship-plan.md` status notes for remaining external gates (frontend, demo video)

## 7. Verification

- [ ] 7.1 Run `python -m pytest tests/ -q` (or targeted suites added above) and fix regressions
- [ ] 7.2 Run smoke against local (and prod when available); record results in `production.md`
- [ ] 7.3 Run `python evals/run_eval.py` against a seeded workspace; record pass rate in README or `evals/README.md`
