## Why

On the deploy-first path, 7P.4–7P.5 and thin CI (7P.7) are done; the next platform gate is **7P.6** — a lean post-deploy smoke script plus soft AI health so operators (and later CD) can prove hard readiness without treating Qdrant/LLM as deploy blockers. Without `scripts/smoke_prod.py` and optional `GET /health/ai`, 7P.8 has nothing repeatable to run after `health-check.sh`.

## What Changes

- Add `scripts/smoke_prod.py`: configurable base URL; hard checks for `GET /health`, auth register/login (or env credentials), and note create; exit non-zero on hard failure
- Add `GET /health/ai` as a **soft** readiness probe (Qdrant when enabled) that MUST NOT be required by hard deploy smoke
- Document post-deploy smoke in `docs/deployment/runbook.md` (env vars, local vs prod base URL)
- Mark `docs/documentation/production.md` step **7P.6** as done when the above lands
- Do **not** implement CD (`deploy.yml` / 7P.8), evals, HITL, or change local Compose defaults
- Do **not** replace `scripts/e2e_docker_smoke.py` — that remains the broader local E2E; `smoke_prod.py` is the lean deploy gate

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Tighten smoke and soft-AI-health requirements to the concrete 7P.6 deliverables (`scripts/smoke_prod.py` hard steps, optional file/automation soft checks, `GET /health/ai` soft probe, runbook post-deploy section, tracker close for 7P.6).

## Impact

- **Code:** `src/core/health.py` (or small sibling module) for `/health/ai`; new `scripts/smoke_prod.py` (prefer `httpx`, patterns from `scripts/e2e_docker_smoke.py`)
- **Docs:** `docs/deployment/runbook.md` post-deploy smoke section; `docs/documentation/production.md` tracker
- **OpenSpec:** delta under `production-platform`
- **Prerequisite (hygiene, not in this change):** 7P.5 runbook/scripts exist on disk but are still uncommitted — commit that tree before or alongside applying this change so main matches the tracker
- **Out of scope:** real VPS first-boot, CD workflow, TLS install, eval harness, HITL, frontend
