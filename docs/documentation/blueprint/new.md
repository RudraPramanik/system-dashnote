###
My Review
Slice 8X.1 — CI

What's correct:

Inventory-first (8X.1.0) before writing YAML is exactly right
No prod secrets in CI is a hard law — correctly enforced
pytest + docker build only, no deploy — right scope for a PR gate
needs: [test] on build job — correct dependency

What needs fixing — 4 issues:

Issue 1 — Wrong Python version
The workflow uses python 3.12 but your blueprint and codebase use python:3.11-slim in Dockerfile. This mismatch can cause subtle CI failures where tests pass locally but fail in CI due to 3.12 syntax changes or package compatibility differences.

Issue 2 — No service containers for test DB/Redis
Your tests/conftest.py likely sets DATABASE_URL and REDIS_URL as stubs or env defaults. But if any test actually hits a DB or Redis (even indirectly through imports), the CI job needs services: for postgres and redis. The inventory step must explicitly check this.

Issue 3 — libmagic1 missing from CI
Your Dockerfile installs libmagic1 for python-magic. Your tests/conftest.py stubs magic on Windows, but CI runs on ubuntu-latest where the real libmagic1 may or may not be installed. The workflow must explicitly apt-get install libmagic1 in the test job — matching what the Dockerfile does.

Issue 4 — PYTHONPATH not set in CI job
Your project uses pythonpath = src in pytest.ini. The GitHub Actions runner won't inherit this automatically without the env being set explicitly in the workflow. Missing this causes ModuleNotFoundError on every test.

Slice 8X.2 — Evaluation Harness

What's correct:

JSONL golden corpus format is the right choice — portable, diffable, easy to extend
Tenant isolation as a first-class eval theme is correct and critical
"forbid surprise create" agent trajectory case is excellent — catches the most dangerous agent behavior
Honest pass-rate documentation law is important

What needs fixing — 5 issues:

Issue 1 — Eval runner calls live API without auth fixture
The runner uses --token from the command line. For CI, you need a way to get a test token without a running auth server. Either the runner supports fixture mode (pre-recorded responses) or the CI eval job is explicitly live-only and never blocks PRs. The distinction must be in the workflow, not just in docs.

Issue 2 — Tenant isolation test needs two real workspaces
The isolation golden says "member B must not see A's private note." But B and A require two separate JWT tokens from two real workspaces. In CI without a live DB, this can't be tested with real tokens. The eval must have a fixture/recorded mode OR be explicitly marked as live-only operator run.

Issue 3 — Agent trajectory scoring is underspecified
"Assert tool sequence" for agent trajectories is vague. The runner needs to know: does it assert the exact sequence of tools called, or just presence/absence? Does it assert the final answer content? Does it assert DB state? These need to be explicit fields in the JSONL schema.

Issue 4 — evals/ lives outside src/ but references internal modules
The runner at evals/run_eval.py likely imports from src/ for fixtures or schemas. This creates a PYTHONPATH problem — the runner needs src on its path to import shared schemas. The README must document this.

Issue 5 — No golden corpus seeding strategy
The eval golden files reference specific note_id and chunk_id values. These don't exist in a fresh environment. The runner needs either: (a) a seed script that creates test notes and returns their IDs, or (b) a fixture mode that doesn't require real IDs. This is the most common eval harness failure mode.

Slice 8X.3 — HITL

What's correct:

API-first (no frontend required for the gate) is correct
Reusing existing checkpointer + thread_id is exactly right — no second persistence system
Separating search/summarize (non-blocking) from create/update (HITL-required) is correct
Resume via thread_id is the right pattern

What needs fixing — 5 issues:

Issue 1 — LangGraph interrupt API version dependency
The slice says "interrupt before create/update" but doesn't specify which LangGraph version's interrupt API to use. LangGraph's interrupt mechanism changed significantly between 0.1.x and 0.2.x. Your requirements.txt has langgraph>=0.1.0 — too loose. The HITL implementation must pin or check the installed version and use the correct API. LangGraph 0.2+ uses interrupt() function; earlier versions use NodeInterrupt.

Issue 2 — Resume endpoint tenant validation
When the client calls the resume endpoint with a thread_id, the endpoint must re-validate that the thread_id belongs to the current authenticated user's workspace. The checkpointer state contains the original workspace_id — it must be compared to ctx.workspace_id before resuming. The slice doesn't mention this check.

Issue 3 — SSE stream stays open during HITL wait
When the agent hits an interrupt mid-stream, the SSE connection is still open. The client receives approval_required and must either keep the connection open or reconnect for the resume. The slice doesn't address what happens to the SSE connection after the interrupt event — does it close? Does it stay open? This must be explicit.

Issue 4 — Pending action storage not addressed
When an action is blocked (requires_approval=True), where is it stored while waiting for user approval? The AutomationDecisionEngine from Slice 7 logs it but doesn't persist it. For HITL to work, there needs to be a pending_actions table or at minimum a Redis key with the interrupt state. The slice says "script proves approve and reject" but doesn't address persistence of the pending state.

Issue 5 — approval_required event naming conflicts
Your Slice 4 stream event taxonomy is: token, metadata, error, [DONE]. Slice 6 added tool_start, tool_end, done. Adding approval_required is fine but the slice says "align event naming with existing SSE JSON shapes" without specifying the exact shape. It must be explicit: {"type": "approval_required", "tool": "create_note", "args": {...}, "thread_id": "...", "interrupt_id": "..."}

####


# Slice 8X.1 — Thin CI (GitHub Actions)
## Final Cursor Prompts (4 Sub-steps, Dev-Safe, No Prod Secrets)

> **When to run:** After Slice 7 automation is stable.
> **Goal:** PR seatbelt — pytest + Docker image build. No deploy. No VPS secrets.
> **Python version:** 3.11 (matches `python:3.11-slim` in Dockerfile — never 3.12)

---

## Slice Overview

```
8X.1.0  Inventory       conftest, pytest.ini, requirements, libmagic, PYTHONPATH baseline
8X.1.1  Workflow stub   .github/workflows/ci.yml triggers + job shells
8X.1.2  Test job green  service containers, apt packages, env aligned to conftest
8X.1.3  Build + gate    docker build needs: test; final checklist
```

**One Composer session = one sub-step. Do not skip 8X.1.0.**

---

## Readiness Gate (before 8X.1.0)

| Prerequisite | Expected | Action if missing |
|---|---|---|
| Repo on GitHub | Remote exists | Create remote before relying on Actions UI |
| `pytest.ini` | `pythonpath = src`, `testpaths = tests` | Verify — do not rewrite |
| `tests/conftest.py` | Sets `JWT_SECRET`, stubs `magic`, DB/Redis env defaults | Read carefully before inventing CI env |
| `Dockerfile` | `python:3.11-slim`, installs `libmagic1` | Verify — never rewrite |
| Local `pytest -q` | Mostly green | Fix red tests before CI — do not skip to force green |
| Live LLM keys in CI | **Not required** | Never add as required secrets for green PR |

---

## ARCHITECTURE LAW — Slice 8X.1 CI
### Paste as your FIRST message in every Composer session for 8X.1.x

```
ARCHITECTURE LAW — DashNoteSystem Slice 8X.1 (Thin CI).

PYTHON VERSION LAW:
  Always python 3.11 in CI — matches python:3.11-slim in Dockerfile.
  Never use 3.12 — version mismatch causes subtle package failures.

CI SCOPE LAW:
  Workflow: pytest + docker build ONLY.
  No SSH deploy. No production VPS secrets. No required live LLM/Qdrant keys.
  Green PR must work with fixture/stub-friendly env from tests/conftest.py.

PYTHONPATH LAW:
  pytest.ini sets pythonpath = src. CI job MUST set PYTHONPATH=src explicitly.
  Without this: every import fails with ModuleNotFoundError in Actions runner.

SYSTEM PACKAGES LAW:
  Dockerfile installs: libmagic1, curl (and others).
  CI test job MUST install the same apt packages the Dockerfile installs.
  Read Dockerfile apt-get RUN layer BEFORE writing the CI apt-get step.
  Never invent packages that are not in Dockerfile.

SERVICE CONTAINERS LAW:
  Read tests/conftest.py carefully.
  If any test imports touch DB or Redis (even through Settings validation),
  the CI job needs postgres and redis service containers.
  Default assumption: add both. Remove only if inventory proves neither needed.

LOCAL DEV LAW:
  Never edit docker-compose.yml, Dockerfile, or settings to make CI easier
  in ways that break local `docker compose up` full stack.

REQUIREMENTS LAW:
  Read Dockerfile — find which requirements file it installs.
  CI pip install must use the SAME file. Do not invent a third requirements tree.

SCOPE LAW:
  New files: .github/workflows/ci.yml only (+ optional short docs note).
  Do NOT implement CD, R2, smoke_prod, evals, or HITL in this slice.

Acknowledge these laws before writing any code.
```

---

## Sub-step 8X.1.0 — Inventory (Read-Only)

**Goal:** Ground truth report before writing any YAML. No files created yet.

**Files to open in Cursor:**
- `tests/conftest.py`
- `pytest.ini`
- `Dockerfile`
- `requirements.txt` (and `requirements/base.txt` if it exists)

---

```
ROLE: You are a senior platform engineer doing a read-only CI readiness audit.

OBJECTIVE: Sub-step 8X.1.0 — Inventory report only. DO NOT create
.github/workflows/ci.yml yet. Produce a written report covering all items below.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.

TASKS:

1. Read tests/conftest.py — Report:
   a. What env vars does it set via os.environ.setdefault()?
      List every variable name and value.
   b. Does it stub the `magic` module? What does the stub look like?
   c. Does it create any DB sessions or Redis connections directly?
   d. Does it use any pytest fixtures that require live services?

2. Read pytest.ini — Report:
   a. Exact pythonpath setting
   b. Exact testpaths setting
   c. asyncio_mode setting
   d. Any addopts that affect CI (e.g. --import-mode)

3. Read Dockerfile — Report:
   a. Base image (must be python:3.11-slim — flag if different)
   b. Exact apt-get packages installed (libmagic1, curl, etc.)
   c. Which requirements file is pip-installed
   d. PYTHONPATH or WORKDIR set

4. Read requirements.txt (and requirements/base.txt if exists) — Report:
   a. Which file the Dockerfile installs
   b. Whether test packages (pytest, pytest-asyncio) are in that file
      or in a separate dev requirements file
   c. Recommendation: which file CI should pip-install

5. Run local baseline (or cite last known result):
   python -m pytest -q 2>&1 | tail -20
   Report: how many pass, how many fail, any import errors.
   If largely red: STOP — list specific failing modules before proceeding.

6. List secrets that MUST NOT appear in CI workflow as required secrets:
   (e.g. OPENAI_API_KEY, QDRANT_API_KEY, DATABASE_URL pointing to prod)

7. Verdict:
   READY — all items accounted for, proceed to 8X.1.1
   BLOCKED — list specific issues that must be resolved first

Do not create any files. This is a report only.
```

**Gate:** Written inventory with READY/BLOCKED verdict.

**Commit:** None required (report only).

---

## Sub-step 8X.1.1 — Workflow Skeleton

**Goal:** Create `.github/workflows/ci.yml` with correct triggers, Python 3.11,
and job structure. Test job may still fail — structure must be correct.

**Files to create:**
- `.github/workflows/ci.yml`

**Do NOT touch:** `docker-compose.yml`, `Dockerfile`, app source

---

```
ROLE: You are a senior platform engineer on DashNoteSystem.

OBJECTIVE: Sub-step 8X.1.1 — Create .github/workflows/ci.yml skeleton.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.0 inventory is READY.
Reference: use the exact values from the inventory report.

TASK: CREATE .github/workflows/ci.yml with this exact structure:

name: CI

on:
  pull_request:
  push:
    branches: [main]    # adjust to repo default branch if different

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      # Include these if inventory found any DB/Redis usage in tests
      # Remove if inventory confirmed tests are fully stubbed
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: dashnote
          POSTGRES_PASSWORD: password
          POSTGRES_DB: dashnote
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    env:
      # Match EXACTLY what tests/conftest.py os.environ.setdefault() sets
      # Use the inventory report — do not invent variables
      PYTHONPATH: src          # MANDATORY — matches pytest.ini pythonpath = src
      DATABASE_URL: postgresql+asyncpg://dashnote:password@localhost:5432/dashnote
      REDIS_URL: redis://localhost:6379
      JWT_SECRET: ci-test-secret-minimum-32-characters-xx
      JWT_REFRESH_SECRET: ci-test-refresh-secret-32-chars-x
      STORAGE_BACKEND: local
      LOCAL_STORAGE_PATH: /tmp/test_storage
      # AI keys intentionally absent — tests must not require these for green CI
      # OPENAI_API_KEY: (never add to CI as required secret)

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"    # MUST match Dockerfile python:3.11-slim
          cache: pip

      - name: Install system packages
        run: |
          sudo apt-get update
          # Install EXACTLY the same apt packages as Dockerfile
          # Read Dockerfile RUN apt-get layer and copy here
          sudo apt-get install -y --no-install-recommends \
            libmagic1 \
            curl
          # Add other packages from Dockerfile if present

      - name: Install Python dependencies
        run: |
          pip install --upgrade pip
          # Use EXACTLY the same requirements file as Dockerfile
          # From inventory: adjust path if requirements/base.txt vs requirements.txt
          pip install -r requirements.txt

      - name: Run tests
        run: python -m pytest -q

  build:
    runs-on: ubuntu-latest
    needs: [test]    # build only if tests pass

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t dashnote-api:ci .
        # No registry push — just verifies build succeeds
        # No LLM API keys needed for build

RULES:
- Python version must be "3.11" — never "3.12" or "3.x"
- PYTHONPATH: src is MANDATORY in env — do not omit
- All env values must match conftest.py setdefault() values exactly
- Service containers: include if inventory found any live service usage;
  if inventory confirmed fully stubbed, remove service containers section
- No production secrets anywhere in this file
- No SSH, no registry push with prod credentials, no deploy steps
- Show me the complete ci.yml — no truncation
```

**Gate:** `ci.yml` exists, valid YAML, no prod secrets, Python 3.11.

**Commit:**
```bash
git commit -am "ci(platform): add PR workflow skeleton for pytest and docker build"
```

---

## Sub-step 8X.1.2 — Test Job Green

**Goal:** `test` job passes on GitHub Actions without live LLM/Qdrant/VPS.

**Allowed fixes:**
- CI env alignment with conftest
- apt packages from Dockerfile
- Missing PYTHONPATH
- Service container configuration

**NOT allowed:**
- Mass `# noqa` or deleting tests
- Disabling half the suite without explicit documented allowlist
- Adding `OPENAI_API_KEY` as required CI secret

---

```
ROLE: You are a senior platform engineer on DashNoteSystem.

OBJECTIVE: Sub-step 8X.1.2 — Make the CI test job green.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.1 skeleton exists; check Actions run result.

If the test job is failing, diagnose by reading the Actions failure log.
Common failure categories and fixes:

CATEGORY 1 — ModuleNotFoundError:
  Root cause: PYTHONPATH not set or set wrong.
  Fix: ensure `PYTHONPATH: src` is in job env (not just pytest.ini).
  pytest.ini pythonpath is read by pytest but not by Python's import system
  before pytest starts in some CI environments.

CATEGORY 2 — Missing system library (libmagic, etc.):
  Root cause: apt-get in CI doesn't match Dockerfile.
  Fix: read Dockerfile apt-get layer exactly; copy same packages to CI apt step.
  Never add packages not in Dockerfile.

CATEGORY 3 — Settings validation error on import:
  Root cause: Settings requires a field that conftest.py doesn't set.
  Fix: add the missing env var to CI job env with a safe test value.
  Read the Settings class — find any field without a default that conftest misses.
  Never use real API keys — use placeholder strings that pass validation.

CATEGORY 4 — DB connection error:
  Root cause: test actually hits PostgreSQL even with stub env.
  Fix: add postgres service container (already in skeleton if inventory flagged this).
  Alternatively, check if conftest.py can stub the DB session completely.

CATEGORY 5 — Import errors from AI modules (litellm, qdrant-client, etc.):
  Root cause: packages not in requirements file that CI installs.
  Fix: check which requirements file CI installs vs which the Dockerfile installs.
  They must be the same file.

TASK:
  1. Read the failing Actions log and identify which category the failure falls into.
  2. Apply the minimum fix — never change more than necessary.
  3. If a test genuinely requires live LLM/Qdrant and cannot be mocked:
     Mark it with @pytest.mark.live and exclude from CI:
     In pytest.ini addopts: add --ignore-glob="*live*" or similar.
     Document the allowlist explicitly in a comment in ci.yml:
     # Tests marked @pytest.mark.live require OPENAI_API_KEY — excluded from PR CI.
  4. Verify local compose still starts correctly after any changes.

GATE:
  - test job green on Actions (or documented allowlist only).
  - No production secrets used to achieve green.
  - Local `docker compose up -d --build` still works.

Show me only the changed lines with surrounding context.
```

**Gate:** Test job green with honest allowlist if any.

**Commit:**
```bash
git commit -am "ci(platform): green pytest job without prod secrets"
```

---

## Sub-step 8X.1.3 — Docker Build Job + Final Gate

**Goal:** `build` job succeeds after `test`. CI is complete.

---

```
ROLE: You are a senior platform engineer on DashNoteSystem.

OBJECTIVE: Sub-step 8X.1.3 — Verify docker build job and close 8X.1 gate.

Paste ARCHITECTURE LAW — Slice 8X.1 CI first.
Prerequisite: 8X.1.2 test job green.

TASKS:

1. Verify build job in ci.yml:
   - needs: [test] must be present — build never runs if tests fail
   - command: docker build -t dashnote-api:ci .
   - No registry login with prod credentials
   - No LLM API keys passed as build args
   - No --secret flags requiring prod keys

2. If build fails, diagnose:
   CATEGORY A — pip install fails during build:
     Packages may have been added to requirements.txt that need system libs
     not yet in Dockerfile. Fix: add system lib to Dockerfile apt-get layer.
   CATEGORY B — Missing file at COPY time:
     Dockerfile COPY instruction references a file that doesn't exist.
     Fix: create the missing file or adjust COPY.
   CATEGORY C — Python syntax error in new code:
     Fix: run python -m py_compile src/path/to/file.py locally first.

3. Add brief docs note (optional — only if not already documented):
   In README.md or docs/, add:
   ## Running tests locally before pushing
   python -m pytest -q
   # Or with coverage:
   python -m pytest -q --cov=src tests/

GATE (8X.1 complete):
  ✅ PR CI: pytest + docker build pass without production secrets
  ✅ Python 3.11 used throughout (matches Dockerfile)
  ✅ PYTHONPATH: src set in CI env
  ✅ System packages match Dockerfile apt-get layer
  ✅ Local docker compose up -d --build still works

Show me verification commands to run manually:
  - Push a PR and check Actions tab
  - docker build -t dashnote-api:test . (local verification)
```

**Gate:** Full thin CI green.

**Commit:**
```bash
git commit -am "ci(platform): docker build job, thin CI complete"
```

---

## Slice 8X.1 Complete — Checklist

```
[ ] 8X.1.0  Inventory READY verdict
[ ] 8X.1.1  ci.yml skeleton (Python 3.11, no prod secrets, PYTHONPATH: src)
[ ] 8X.1.2  test job green (honest allowlist if any)
[ ] 8X.1.3  docker build job green; local compose untouched
```