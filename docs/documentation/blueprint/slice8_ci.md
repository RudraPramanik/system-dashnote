# Slice 8X.1 — Thin CI (GitHub Actions)
## Final Cursor Prompts (4 Sub-steps, Dev-Safe, No Prod Secrets)

> **Parent index:** [`slice8_X.md`](slice8_X.md) (ship order + global 8X law)  
> **Also:** [`slice-platform.md`](slice-platform.md) §7P.7 · [`production.md`](../production.md) tracker  
> **When to run:** After 7P.0–7P.3; before or independent of 7P.4–7P.6.  
> **Goal:** PR seatbelt — pytest + Docker image build. No deploy. No VPS secrets.

---

## Slice Overview

```
8X.1.0  Inventory       conftest, pytest.ini, requirements, local pytest baseline
8X.1.1  Workflow stub   .github/workflows/ci.yml triggers + job shells
8X.1.2  Test job green  env aligned to fixtures; CI-blocking fixes only
8X.1.3  Build + gate    docker build needs: test; mark 7P.7 ✅
```

**One Composer session ≈ one substep.** Do not skip 8X.1.0.

---

## Readiness gate (before 8X.1.0)

| Prerequisite | Expected | Action if missing |
|--------------|----------|-------------------|
| Repo on GitHub (or about to push) | Remote exists | Create remote before relying on Actions UI |
| `pytest.ini` | `pythonpath = src`, `testpaths = tests` | Already present — verify |
| `tests/conftest.py` | Sets test JWT secrets / stubs | Read before inventing CI env |
| `Dockerfile` | Builds from `requirements/base.txt` | Already present — verify |
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

CI LAW:
  Workflow: pytest + docker build ONLY.
  No SSH deploy, no production VPS secrets, no required live LLM/Qdrant keys.
  Green PR must work with fixture/stub-friendly env (see tests/conftest.py).

REQUIREMENTS:
  Dockerfile installs requirements/base.txt — CI pip install should match that
  (or requirements.txt if inventory proves that is the test install path).
  Read first; do not invent a third requirements tree.

SCOPE:
  NEW preferred: .github/workflows/ci.yml
  Optional short docs note only if needed.
  Do NOT implement CD (7P.8), R2, smoke_prod, evals, or HITL in this slice.

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

---

## Sub-step 8X.1.0 — Inventory

**Goal:** Ground truth report before writing YAML. No workflow file required yet.

**Read (do not rewrite unless broken):**

- `tests/conftest.py` — env defaults (`JWT_SECRET`, Redis stubs, magic stub)
- `pytest.ini`
- `requirements/base.txt`, `requirements.txt`, `requirements/_all.txt`
- `Dockerfile`
- `docs/documentation/blueprint/slice-platform.md` §7P.7

---

```
ROLE: Senior platform engineer (read-only inventory).

OBJECTIVE: Slice 8X.1.0 — CI readiness inventory. Produce a short written report.
Do NOT create .github/workflows/ci.yml yet unless the human explicitly expands scope.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.

TASKS:
  1. Summarize how tests expect env (from conftest.py / pytest.ini).
  2. State which requirements file Dockerfile uses and which CI should pip-install.
  3. Run (or cite last known) `python -m pytest -q` baseline:
     - If largely green → proceed verdict.
     - If red → list failing areas; STOP or propose minimal fixes only.
  4. List secrets that must NOT appear in CI.
  5. End with verdict: READY for 8X.1.1 | BLOCKED (reasons).

GATE:
  - Written inventory exists (chat report or docs note).
  - Verdict READY, or BLOCKED with concrete fixes listed.
```

**Gate:** Inventory complete with READY/BLOCKED verdict.

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
Prerequisite: 8X.1.0 READY.

TASKS:
  1. CREATE .github/workflows/ci.yml
     on:
       pull_request:
       push:
         branches: [main]   # or repo default branch — verify
     jobs:
       test:
         runs-on: ubuntu-latest
         steps: checkout, setup-python 3.12, pip install (path from inventory),
                placeholder or initial pytest -q
         env: match conftest defaults (JWT_SECRET, etc.) — NO prod secrets
       build:
         runs-on: ubuntu-latest
         needs: [test]
         steps: checkout, docker build .
         # may leave build failing until 8X.1.3 if test not green yet —
         # prefer stubbing build steps only if test job is still being fixed in 8X.1.2
  2. Do not add SSH, registry login with prod creds, or deploy jobs.

GATE:
  - ci.yml exists and is valid YAML.
  - No production secrets referenced.
  - Workflow is discoverable on next push/PR (when remote exists).
```

**Gate:** Skeleton committed; no prod secrets.

**Commit hint:** `ci(platform): add PR workflow skeleton for pytest and docker build`

---

## Sub-step 8X.1.2 — Test job green

**Goal:** `test` job passes on GitHub without live LLM/Qdrant/VPS.

**Allowed fixes:** CI env, dependency install path, missing apt packages that tests need (e.g. patterns already in Dockerfile like `libmagic1` if tests import magic for real).  
**Disallowed:** Mass `# noqa` / deleting tests / disabling half the suite without allowlist from 8X.1.0.

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Slice 8X.1.2 — Make the CI test job green without prod or live LLM secrets.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.1 skeleton exists.

TASKS:
  1. Align job `env` with tests/conftest.py setdefaults and any required Settings fields.
  2. Ensure pip install uses the inventory-chosen requirements file.
  3. If CI needs system libs that Dockerfile already installs (e.g. libmagic1),
     add the same apt packages to the test job — do not invent unrelated stacks.
  4. Iterate until `pytest -q` is green on Actions (or only allowlisted failures remain,
     documented in workflow comments or a tiny docs/ci note).
  5. Do not add OPENAI_API_KEY / QDRANT_API_KEY as required secrets for green.

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
  - production.md 7P.7 checked off.
  - Local docker-compose path not broken.
```

**Gate:** Full thin CI green; tracker updated.

**Commit hint:** `ci(platform): add docker build job and mark 7P.7 complete`

---

## Slice 8X.1 Complete — Checklist

```
[ ] 8X.1.0 Inventory READY
[ ] 8X.1.1 ci.yml skeleton (no prod secrets)
[ ] 8X.1.2 test job green
[ ] 8X.1.3 docker build job green; production.md 7P.7 ✅
```

**Next:** [`slice8_eval.md`](slice8_eval.md) (8X.2) · Parent: [`slice8_X.md`](slice8_X.md)
