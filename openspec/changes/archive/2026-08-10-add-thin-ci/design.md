## Context

Platform foundation (7P.0–7P.3) is complete. The deploy-first ship path (`slice8_X.md`) places **8X.1 Thin CI / 7P.7** next: a PR seatbelt before finishing R2, deploy scripts, smoke, and VPS CD. No `.github/workflows/` exists yet. Local pytest is configured via `pytest.ini` (`pythonpath = src`) and `tests/conftest.py` (magic stub, `DATABASE_URL` / `JWT_SECRET` setdefaults). The single `Dockerfile` uses `python:3.12-slim`, installs `libmagic1`, and pip-installs `requirements/base.txt`. Executable prompts live in `docs/documentation/blueprint/slice8_ci.md`.

## Goals / Non-Goals

**Goals:**
- Inventory-first CI readiness report (READY/BLOCKED + service-container verdict)
- GitHub Actions workflow: pytest then `docker build`, triggered on PR and pushes to the default branch
- Dockerfile parity for Python version and apt packages; env aligned to conftest (no invented credentials)
- Mark `production.md` 7P.7 when the gate is green
- Preserve local `docker compose up` behavior

**Non-Goals:**
- CD / SSH / VPS deploy (7P.8)
- R2 contract, deploy scripts, smoke_prod (7P.4–7P.6)
- Eval harness (8X.2) or HITL (8X.3)
- Required live `OPENAI_*` / `NVIDIA_*` / `QDRANT_*` / prod `DATABASE_URL` secrets for green PR
- Rewriting `conftest.py` or inventing a second requirements tree for “CI convenience”
- Treating `docs/documentation/blueprint/new.md` as source of truth (stale 3.11 guidance)

## Decisions

### 1. Inventory before YAML (8X.1.0)
- **Choice:** Written report covering conftest, pytest.ini, Dockerfile, requirements path, local pytest baseline, forbidden secrets, and whether GitHub Actions `services:` for postgres/redis are needed — then READY or BLOCKED.
- **Why:** Avoids cargo-culting service containers and wrong Python/apt from review scratchpads.
- **Alternatives:** Jump straight to `ci.yml` — rejected; blueprint forbids skipping 8X.1.0.

### 2. One workflow file, two jobs
- **Choice:** `.github/workflows/ci.yml` with `test` then `build` (`needs: [test]`).
- **Why:** Matches thin-CI scope in `production-platform` and `slice8_ci.md`; keeps CD out of this change.
- **Alternatives:** Combined single job — weaker failure isolation; matrix or nightly live smoke — out of scope.

### 3. Dockerfile is the parity source of truth
- **Choice:** `setup-python` version and apt packages MUST match the current Dockerfile (`3.12` / `libmagic1` today). If Dockerfile later changes, inventory + CI follow.
- **Why:** Prevents 3.11 drift from stale review docs (`new.md`).
- **Alternatives:** Pin forever to 3.11 or 3.12 in law — rejected; law is “match Dockerfile.”

### 4. Requirements install path
- **Choice:** Prefer pip-install of whatever the Dockerfile installs (`requirements/base.txt` today). If inventory proves tests need extras from another file, document and install that path explicitly — do not invent a third tree.
- **Why:** Same dependency surface as the image under `build`.

### 5. Service containers only when proven
- **Choice:** Add postgres/redis Actions services only if 8X.1.0 shows tests need live services; align credentials to conftest setdefaults when env is listed.
- **Why:** Many tests use sqlite/fakes; blind services with invented passwords cause false confidence and flaky jobs.
- **Alternatives:** Always add both services — rejected without inventory evidence.

### 6. PYTHONPATH belt-and-suspenders
- **Choice:** Keep `pytest.ini` `pythonpath = src` and also set job env `PYTHONPATH: src`.
- **Why:** Defensive for Actions / non-pytest steps; do not claim every import fails without the env var alone.

### 7. Tracker update at the end
- **Choice:** Flip `production.md` 7P.7 to ✅ only after pytest + docker build succeed without prod secrets.
- **Why:** Tracker must reflect reality, not skeleton presence.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Local pytest largely red → CI never honestly green | 8X.1.0 STOP or explicit allowlist; no mass skips |
| Inventory wrong on services → connection failures in CI | Cite evidence (live PG/Redis vs fakes); iterate only with category fixes |
| Agent follows `new.md` Python 3.11 | Architecture law + design: match Dockerfile only |
| Temptation to add CD in the same PR | Explicit non-goal; reject SSH/registry-prod in review |
| Apt/`libmagic` missing on ubuntu runner | Install Dockerfile apt packages in test job (8X.1.2) |
| Editing compose “for CI” breaks local stack | Never edit `docker-compose.yml` for CI convenience |

## Migration Plan

1. Complete 8X.1.0 inventory (report only; no workflow required).
2. Add skeleton `ci.yml` (8X.1.1).
3. Green the test job (8X.1.2).
4. Confirm build job + mark 7P.7 (8X.1.3).
5. Rollback: delete or disable the workflow file; local compose unchanged. No data migration.

## Open Questions

- Service-container verdict (READY-without-services vs NEED postgres/redis) — resolved only by 8X.1.0 inventory.
- Exact default branch name for `push:` triggers — verify at skeleton time (`main` vs repo default).
- Whether any test extras beyond `requirements/base.txt` are required — resolved by inventory.
