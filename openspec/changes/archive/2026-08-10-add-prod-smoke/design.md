## Context

Deploy-first platform path: 7P.0–7P.5 and thin CI (7P.7) are complete on the tracker. `GET /health` already gates Postgres + Redis only. Soft Qdrant boot (7P.3) exists, but there is no `GET /health/ai` and no lean `scripts/smoke_prod.py`. `scripts/e2e_docker_smoke.py` is a broad local E2E (notes CRUD, files, refresh, AI search wait) — too heavy and AI-coupled to be the CD hard gate.

OpenSpec already requires a smoke script (health + auth + note create) and soft AI health; this change makes those concrete and closes tracker **7P.6**.

## Goals / Non-Goals

**Goals:**

- Ship a lean, URL-configurable smoke script that exits 0 only when hard platform paths work
- Expose soft AI/Qdrant readiness without changing hard `/health` semantics
- Document how operators run smoke after `health-check.sh`
- Close 7P.6 on the production tracker

**Non-Goals:**

- CD workflow / SSH deploy (7P.8)
- Replacing or deleting `e2e_docker_smoke.py`
- Making Qdrant or LLM required for deploy success
- Evals, HITL, frontend, TLS implementation
- Committing live credentials or VPS secrets

## Decisions

1. **Separate `smoke_prod.py` from `e2e_docker_smoke.py`**  
   Rationale: CD needs a short hard gate; E2E remains the richer local proof.  
   Alternative: wrap E2E with `--mode=prod` — rejected (too many soft steps would confuse exit codes).

2. **Hard smoke steps (must pass for exit 0)**  
   Align with OpenSpec: `GET /health` (200 + database reachable), auth (register fresh user **or** login via `SMOKE_EMAIL`/`SMOKE_PASSWORD`), create notebook if needed + `POST /notes/` success.  
   Alternative: require file upload + worker automation poll — keep as **optional soft** step (skip/warn, do not fail hard gate) so deploys are not blocked on LLM/worker latency.

3. **Soft steps (print SKIP/WARN; do not fail hard exit)**  
   Optional: `GET /health/ai`, file upload + short poll for summary/tags, semantic search — only when explicitly enabled (e.g. `--with-ai` or env `SMOKE_SOFT_AI=1`). Default hard run stays AI-free.

4. **`GET /health/ai` on the existing health router**  
   Extend `src/core/health.py` (or tiny sibling imported from `main.py`) to probe Qdrant when `settings.qdrant_enabled`: lightweight connectivity / collection presence. When Qdrant disabled, return a clear “not configured” soft status (200 with degraded/not_configured semantics — document exact JSON in implementation). Never fold Qdrant into hard `/health`.  
   Alternative: put probe under `/ai/*` — rejected; soft readiness belongs next to hard health for operators.

5. **HTTP client + CLI**  
   Use `httpx` sync client + argparse/`SMOKE_BASE_URL` like the existing E2E script. Default base `http://127.0.0.1` (nginx edge), matching deploy health-check.

6. **Auth strategy**  
   Prefer ephemeral register (`smoke-{uuid}@example.com`) for local/prod demos; if `SMOKE_EMAIL` + `SMOKE_PASSWORD` set, login instead (useful when registration is locked down later). Never commit credentials.

7. **Tracker + runbook**  
   Add “Post-deploy smoke” to `docs/deployment/runbook.md`; mark 7P.6 done in `production.md` when script + `/health/ai` + docs land.

## Risks / Trade-offs

- **[Risk] Blueprint 7P.6 text emphasizes file upload + 90s poll as hard** → Mitigation: OpenSpec hard gate is health/auth/note; treat upload/automation as soft/optional and document the divergence in runbook.
- **[Risk] Note create needs notebook first** → Mitigation: smoke creates a notebook (same as E2E) before note create; still one “content write” proof.
- **[Risk] Qdrant client import pulls heavy deps into health path** → Mitigation: lazy-import inside `/health/ai` handler; failures become soft JSON status, never crash the API process.
- **[Risk] Uncommitted 7P.5 tree confuses “done” tracker** → Mitigation: call out as hygiene before merge; not a code dependency for smoke itself.
- **[Trade-off]** Soft AI default-off means first CD won’t prove embeddings — accepted until 7P.8/live URL + optional soft flag.

## Migration Plan

1. Implement `/health/ai` and register (already on health router if extended in place).
2. Add `scripts/smoke_prod.py`; validate against local compose (`SMOKE_BASE_URL=http://127.0.0.1`).
3. Update runbook + mark 7P.6 done.
4. Rollback: remove route + script + revert docs; hard `/health` unchanged so deploys remain safe.

## Open Questions

- None blocking apply. Exact `/health/ai` JSON shape can follow existing `/health` style (`status`, `dependencies`) during implementation.
- Whether soft file-upload step ships in the first apply pass is optional; hard gate alone closes the OpenSpec smoke requirement.
