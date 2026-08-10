# Slice 8X.1 — Thin CI (GitHub Actions)
## Final Cursor Prompts (4 Sub-steps, Dev-Safe, No Prod Secrets)

> **Parent index:** [`slice8_X.md`](slice8_X.md) (ship order + global 8X law)  
> **Also:** [`slice-platform.md`](slice-platform.md) §7P.7 · [`production.md`](../production.md) tracker  
> **When to run:** After 7P.0–7P.3; before or independent of 7P.4–7P.6.  
> **Goal:** PR seatbelt — pytest + Docker image build. No deploy. No VPS secrets.  
> **Python / apt:** Match the repo `Dockerfile` (currently `python:3.12-slim` + `libmagic1`). Never invent 3.11 “because a review said so.”

---

## Slice Overview

```
8X.1.0  Inventory       conftest, pytest.ini, Dockerfile base/apt, requirements, services need, pytest baseline
8X.1.1  Workflow stub   .github/workflows/ci.yml triggers + job shells (Dockerfile Python + PYTHONPATH)
8X.1.2  Test job green  env/apt/services per inventory; failure-category fixes only
8X.1.3  Build + gate    docker build needs: test; mark 7P.7 ✅
```

**One Composer session ≈ one substep.** Do not skip 8X.1.0.

---

## Readiness gate (before 8X.1.0)

| Prerequisite | Expected | Action if missing |
|--------------|----------|-------------------|
| Repo on GitHub (or about to push) | Remote exists | Create remote before relying on Actions UI |
| `pytest.ini` | `pythonpath = src`, `testpaths = tests` | Already present — verify |
| `tests/conftest.py` | Sets test JWT secrets / stubs (e.g. `magic`) | Read before inventing CI env |
| `Dockerfile` | Base image + apt + `requirements/base.txt` | Inventory must record exact tags/packages |
| Local health (optional but wise) | `curl http://127.0.0.1/health` → 200 | Fix stack if you will also smoke locally |
| Live LLM keys in CI | **Not required** | Never add as required secrets for green PR |

**Verdict:** Start **8X.1.0**. Stop if inventory finds unexplained mass test failures — fix or document an allowlist before inventing CI env hacks.

---

## ARCHITECTURE LAW — Slice 8X.1 CI
### Paste as your FIRST message in every Composer session for 8X.1.x

```
ARCHITECTURE LAW — DashNoteSystem Slice 8X.1 (Thin CI / 7P.7).

CRITICAL — DO NOT BREAK LOCAL DEV:
  Never edit docker-compose.yml to “make CI easier” in ways that break
  `docker compose up` local full stack (db, redis, qdrant, api, worker, nginx).

DOCKERFILE PARITY LAW:
  CI Python version MUST match Dockerfile base image (currently python:3.12-slim → setup-python "3.12").
  CI apt packages MUST match Dockerfile apt-get layer (currently libmagic1; copy exactly — do not invent stacks).
  NEVER hard-require Python 3.11 when Dockerfile is 3.12. Law is “match Dockerfile,” not a forever pin.
  If Dockerfile later changes base tag, inventory + CI must follow — do not leave drift.

CI LAW:
  Workflow: pytest + docker build ONLY.
  No SSH deploy, no production VPS secrets, no required live LLM/Qdrant keys.
  Green PR must work with fixture/stub-friendly env (see tests/conftest.py).

PYTHONPATH HYGIENE:
  pytest.ini already sets pythonpath = src (primary).
  Also set job env PYTHONPATH: src as belt-and-suspenders.
  Do NOT claim every import inevitably fails without the env var — pytest.ini is real;
  the env var is defensive hygiene for Actions / non-pytest steps.

REQUIREMENTS:
  Dockerfile installs requirements/base.txt — CI pip install should match that
  (or requirements.txt if inventory proves that is the test install path).
  Read first; do not invent a third requirements tree.

SERVICE CONTAINERS:
  Add postgres/redis GitHub Actions services ONLY if 8X.1.0 inventory proves tests need live services.
  Many tests use sqlite + fakes — do not default-add containers with invented credentials.
  When env vars are listed, align values to tests/conftest.py os.environ.setdefault() — do not copy
  unrelated review-scratch credentials.

SCOPE:
  NEW preferred: .github/workflows/ci.yml
  Optional short docs note only if needed.
  Do NOT implement CD (7P.8), R2, smoke_prod, evals, or HITL in this slice.
  Do NOT treat docs/documentation/blueprint/new.md as source of truth.

FALLBACK:
  If local `python -m pytest -q` is largely red → STOP.
  Fix tests or document an explicit allowlist in the inventory report.
  Do not silence failures with broad pytest skips to force CI green.
```

---

## Fallbacks / out of scope

| Situation | Do this |
|-----------|---------|
| Local pytest mostly red | Fix or allowlist in 8X.1.0 — do not proceed to claim CI success |
| Unclear which requirements file CI should use | Prefer `requirements/base.txt` (Dockerfile); note `requirements.txt` if tests need extras |
| Want live API smoke in CI | Defer to 7P.6 / nightly — not PR-required |
| Want CD in same PR | **Out of scope** — 8X.4 / 7P.8 |
| Agent offers to rewrite conftest “for clarity” | Reject unless required for green CI |
| Agent offers Python 3.11 because a review doc said so | Reject — match Dockerfile (currently 3.12) |

---

## Sub-step 8X.1.0 — Inventory

**Goal:** Ground truth report before writing YAML. No workflow file required yet.

**Read (do not rewrite unless broken):**

- `tests/conftest.py` — every `os.environ.setdefault`, magic stub, Redis reset fixtures
- `pytest.ini` — `pythonpath`, `testpaths`, `asyncio_mode`, `addopts`
- `Dockerfile` — `FROM` tag, apt-get packages, which requirements file, WORKDIR/PYTHONPATH
- `requirements/base.txt`, `requirements.txt`, `requirements/_all.txt`
- `docs/documentation/blueprint/slice-platform.md` §7P.7

---

```
ROLE: Senior platform engineer (read-only inventory).

OBJECTIVE: Slice 8X.1.0 — CI readiness inventory. Produce a written report.
Do NOT create .github/workflows/ci.yml yet unless the human explicitly expands scope.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.

TASKS — report MUST cover all of:

  1. tests/conftest.py
     a. List every os.environ.setdefault name and value.
     b. Magic / other stubs (what and why).
     c. Any live DB/Redis connections created in conftest?
     d. Fixtures that require live services?

  2. pytest.ini — pythonpath, testpaths, asyncio_mode, addopts (esp. --import-mode).

  3. Dockerfile
     a. Exact FROM base image (flag if not python:3.12-slim today).
     b. Exact apt-get packages.
     c. Which requirements file is pip-installed.
     d. WORKDIR / PYTHONPATH if set.

  4. Requirements — which file Dockerfile installs; whether pytest lives there or in a
     separate file; which file CI should pip-install.

  5. Service-container verdict:
     READY-without-services | NEED postgres | NEED redis | NEED both
     Cite evidence (tests that hit live PG/Redis vs sqlite/fakes).

  6. Local baseline: run or cite `python -m pytest -q`
     If largely red → STOP; list failing areas.

  7. Secrets that MUST NOT appear as required CI secrets
     (OPENAI_API_KEY, QDRANT_*, prod DATABASE_URL, VPS SSH, etc.).

  8. Verdict: READY for 8X.1.1 | BLOCKED (concrete fixes).

Do not create any workflow files. Report only.
```

**Gate:** Inventory complete with READY/BLOCKED verdict and explicit service-container decision.

**Commit hint:** none required (report-only). Optional: `docs(ci): note pytest baseline for 8X.1` only if you persist the report.

---

## Sub-step 8X.1.1 — Workflow skeleton

**Goal:** Create `.github/workflows/ci.yml` with triggers and job shells. Test job may still be incomplete — but structure must exist.

**Files:**

| Action | Path |
|--------|------|
| CREATE | `.github/workflows/ci.yml` |
| DO NOT TOUCH | `docker-compose.yml`, app source (unless inventory demanded a one-line fix) |

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Slice 8X.1.1 — Add GitHub Actions workflow skeleton (no deploy).

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.0 READY. Use exact values from the inventory report.

TASKS:
  1. CREATE .github/workflows/ci.yml
     on:
       pull_request:
       push:
         branches: [main]   # or repo default branch — verify
     jobs:
       test:
         runs-on: ubuntu-latest
         # services: ONLY if inventory said NEED postgres/redis — else omit
         env:
           PYTHONPATH: src          # belt-and-suspenders (pytest.ini also has pythonpath = src)
           # Other env: copy from conftest setdefaults / inventory — NO invented credentials
           # NO prod secrets, NO required OPENAI_API_KEY
         steps:
           - checkout
           - setup-python with python-version matching Dockerfile
             (currently "3.12" for python:3.12-slim — never invent 3.11)
           - optional apt step stub (fill packages in 8X.1.2 from Dockerfile)
           - pip install inventory-chosen requirements file
           - python -m pytest -q (may still fail until 8X.1.2)
       build:
         runs-on: ubuntu-latest
         needs: [test]
         steps: checkout, docker build .
  2. Do not add SSH, registry login with prod creds, or deploy jobs.

GATE:
  - ci.yml exists and is valid YAML.
  - Python version matches Dockerfile inventory.
  - PYTHONPATH: src present in test job env.
  - No production secrets referenced.
```

**Gate:** Skeleton committed; no prod secrets; Dockerfile Python parity.

**Commit hint:** `ci(platform): add PR workflow skeleton for pytest and docker build`

---

## Sub-step 8X.1.2 — Test job green

**Goal:** `test` job passes on GitHub without live LLM/Qdrant/VPS.

**Allowed fixes:** CI env (aligned to conftest), dependency install path, apt packages from Dockerfile, service containers per inventory, documented allowlist.  
**Disallowed:** Mass `# noqa` / deleting tests / disabling half the suite without allowlist from 8X.1.0; inventing Python 3.11; inventing credentials from review scratchpads.

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Slice 8X.1.2 — Make the CI test job green without prod or live LLM secrets.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.1 skeleton exists; diagnose from Actions log if failing.

TASKS:
  1. Align job `env` with tests/conftest.py setdefaults and any required Settings fields.
     Values must match inventory — do not invent dashnote/password-style credentials
     if conftest uses different user/db names.
  2. Ensure pip install uses the inventory-chosen requirements file.
  3. Install the SAME apt packages as Dockerfile (libmagic1 today). Never invent stacks.
  4. Add postgres/redis services only if 8X.1.0 said NEED_*.
  5. Keep PYTHONPATH: src in job env.
  6. Iterate until pytest -q is green (or only allowlisted failures remain, documented).
  7. Do not add OPENAI_API_KEY / QDRANT_API_KEY as required secrets for green.

FAILURE CATEGORIES (pick the smallest fix):
  CATEGORY 1 — ModuleNotFoundError:
    Confirm PYTHONPATH: src and pytest.ini pythonpath; confirm pip install path.
  CATEGORY 2 — Missing system library (libmagic, etc.):
    Copy Dockerfile apt-get packages into the CI apt step.
  CATEGORY 3 — Settings validation on import:
    Add missing env with safe test placeholders from inventory/Settings — never real API keys.
  CATEGORY 4 — DB connection error:
    Only if inventory said live PG needed: add service container OR confirm tests can stay on sqlite/fakes.
  CATEGORY 5 — Missing AI packages:
    CI must pip-install the same requirements file Dockerfile uses (or inventory-proven test extras).

GATE:
  - test job green on a PR or push (or documented allowlist only).
  - Local compose still intact.
```

**Gate:** Test job green (honest allowlist if any).

**Commit hint:** `ci(platform): green pytest job without prod secrets`

---

## Sub-step 8X.1.3 — Docker build job + CI gate

**Goal:** `build` job succeeds after `test`; mark platform tracker 7P.7 done.

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Slice 8X.1.3 — Docker build job + close 7P.7 / 8X.1 gate.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.2 test job green.

TASKS:
  1. Ensure build job `needs: test` and runs `docker build` against repo Dockerfile.
  2. Confirm build does not require BuildKit secrets for LLM keys.
  3. Update docs/documentation/production.md — mark 7P.7 CI ✅.
  4. Optional: one short paragraph in docs or README on how to run pytest locally before push.

GATE (8X.1 complete):
  - PR CI: pytest + docker build succeed without production secrets.
  - Python/apt match Dockerfile (currently 3.12 + libmagic1).
  - PYTHONPATH: src set in test job env.
  - production.md 7P.7 checked off.
  - Local docker-compose path not broken.
```

**Gate:** Full thin CI green; tracker updated.

**Commit hint:** `ci(platform): add docker build job and mark 7P.7 complete`

---

## Slice 8X.1 Complete — Checklist

```
[ ] 8X.1.0 Inventory READY (incl. service-container verdict)
[ ] 8X.1.1 ci.yml skeleton (Dockerfile Python, PYTHONPATH: src, no prod secrets)
[ ] 8X.1.2 test job green (apt parity; honest allowlist if any)
[ ] 8X.1.3 docker build job green; production.md 7P.7 ✅
```

**Next (chosen / deploy-first):** [`slice-platform.md`](slice-platform.md) §7P.4–7P.6, 7P.8 (8X.4) · Parent: [`slice8_X.md`](slice8_X.md) · Evals later: [`slice8_eval.md`](slice8_eval.md)
