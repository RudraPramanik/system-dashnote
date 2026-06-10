# Slice Platform — Production Deployment & CI/CD
## Final Cursor Prompts (8 Sub-steps, Dev-Safe, Hosted Data Plane)

> **When to run:** After Slices 7 **and 7.5** are complete (automation + LLM hardening in local Docker).
> **Prerequisite done:** Slice 7.5 (`slice7-llm-hardening.md`) — `shared/llm/` retries, structured calls, agent `call_model` hardening ✅
> **Goal:** Shape the repo for production **without breaking local Docker**. Separate prod compose profile. CI/CD and VPS deploy come last, only when the repo is ready.
> **Philosophy (from `total.md`):** Hosted data plane (Postgres, Redis, Qdrant, R2, Grafana Cloud). Thin compute on VPS (api + worker + nginx). Same Dockerfile everywhere.

---

## Slice Overview (this document)

```
Phase A — Repo shape (local dev unchanged)
  7P.0  Discovery audit          Read-only inventory — no file changes
  7P.1  Env contract             .env.example sync + .env.production.example
  7P.2  Prod compose             docker-compose.prod.yml (api, worker, nginx, migrate)
  7P.3  Soft dependency boot     Qdrant bootstrap non-fatal at API/worker startup
  7P.4  Prod storage contract    R2/S3 vars documented; dev stays local volume

Phase B — Deploy readiness (still no VPS required)
  7P.5  Deploy scripts           scripts/deploy/* + docs/deployment.md runbook
  7P.6  Health & smoke           Extended readiness checks; prod smoke script

Phase C — CI/CD (run when repo + secrets are ready)
  7P.7  CI workflow              GitHub Actions: pytest + docker build on PR
  7P.8  CD workflow + gate        Push image, SSH deploy, production gate
```

**Resume feature slices (8–11) only after 7P.8 gate passes on a real VPS.**

---

## Readiness gate (run before Sub-step 7P.1)

| Prerequisite | Expected state | Action if missing |
|--------------|----------------|-------------------|
| Slices 1–7 implemented | `docker compose up` works; file upload automation completes | Finish `slice7.md` |
| Slice 7.5 LLM hardening | `src/shared/llm/` exists; automation uses `acompletion_structured` | ✅ Done — see `slice7-llm-hardening.md` |
| Local health | `curl http://127.0.0.1/health` → 200 | Fix api/db/redis |
| Tests pass | `python -m pytest -q` green | Fix regressions |
| `.env` not committed | `.env` in `.gitignore` | Verify gitignore |
| One Dockerfile | `Dockerfile` at repo root | Already exists |
| Blueprint infra law | Append-only to `docker-compose.yml` for **dev** | Prod uses **new** `docker-compose.prod.yml` only |

**Verdict:** Start 7P.0 audit. Do not create `docker-compose.prod.yml` until 7P.0 report is reviewed.

---

## Target production topology

| Component | Where | Connection |
|-----------|--------|------------|
| `api` | VPS Docker | `env_file: .env` — no compose URL overrides |
| `worker` | VPS Docker | Same `.env` as api |
| `nginx` | VPS Docker | Proxy to `api:8000` |
| `migrate` | VPS one-shot per deploy | `alembic upgrade head` |
| `prometheus` | VPS Docker (optional, ~256MB) | Scrapes `api:8000/metrics` → Grafana Cloud `remote_write` |
| Postgres | Hosted (Neon, Supabase, RDS, …) | `DATABASE_URL` in `.env` |
| Redis | Hosted (Upstash, Redis Cloud, …) | `REDIS_URL` / `ARQ_REDIS_URL` (`rediss://` OK) |
| Qdrant | Qdrant Cloud | `QDRANT_URL` + `QDRANT_API_KEY` |
| Object storage | Cloudflare R2 (recommended) | `STORAGE_BACKEND=r2` |
| Grafana | Grafana Cloud | `GRAFANA_CLOUD_*` via Prometheus remote_write |
| Langfuse / LLM | SaaS + API keys | Optional — must not block deploy |

**VPS runs only:** nginx, api, worker, migrate (one-shot), optional prometheus.

---

## Dependency tiers (enforce in code + docs)

| Tier | Services | Deploy gate |
|------|----------|-------------|
| **Hard** | Postgres, Redis | `/health` must return 200 |
| **Soft** | Qdrant, LLM providers | App boots; AI/automation degrades |
| **Optional** | Langfuse, LangSmith, Grafana remote_write | Never block startup or CD |

---

## ARCHITECTURE LAW — Platform slice
### Paste as your FIRST message in every Cursor Composer session for 7P.x

```
ARCHITECTURE LAW — DashNoteSystem Platform Slice (7P).

CRITICAL — DO NOT BREAK LOCAL DEV:
  docker-compose.yml remains the FULL local dev stack (db, redis, qdrant, api, worker, nginx, prometheus).
  Never remove or rename existing dev services.
  Never change dev service hostnames (db, redis, qdrant) in docker-compose.yml environment blocks
  unless explicitly fixing a documented bug — local dev depends on them.

PROD COMPOSE LAW:
  docker-compose.prod.yml is a NEW file — never merge prod and dev into one file.
  Prod compose includes ONLY: nginx, api, worker, migrate, optional prometheus.
  Prod compose MUST NOT include: db, redis, qdrant.
  Prod compose MUST NOT set DATABASE_URL, REDIS_URL, QDRANT_URL in environment: —
  those come from env_file: .env only (plus safe overrides: DEBUG=false).
  Dev compose MAY keep explicit environment: overrides pointing at local service names.

ENV LAW:
  src/config.py is the single source of truth for variable names.
  .env.example documents every Settings field (grouped by slice).
  .env.production.example documents hosted URLs and prod-only values (no real secrets).
  Never commit .env or production secrets.
  api and worker in BOTH profiles use env_file: .env.

DOCKERFILE LAW:
  One Dockerfile for api, worker, and migrate — no new Dockerfiles.
  CMD stays uvicorn for api; worker overrides command in compose.

STORAGE LAW (prod):
  STORAGE_BACKEND=r2 (or s3/minio) on VPS — api and worker share no local volume.
  Dev keeps STORAGE_BACKEND=local + local_storage volume — unchanged.

SOFT DEPENDENCY LAW:
  Qdrant collection bootstrap at startup must be non-fatal (try/except + log).
  Pattern already exists for LangGraph checkpointer in main.py — mirror that.
  LLM keys missing → ai_enabled=False — already in config.py; do not regress.

CI/CD LAW:
  PR workflow: pytest + docker build only — no deploy, no production secrets required.
  CD workflow: build push image → SSH VPS → migrate → rolling api → worker → health check.
  Never deploy if pytest fails.

IMPORT / CODE LAW (unchanged from feature slices):
  from config import settings, get_settings — never from src.config
  Do not refactor domain routers or AI logic in this slice unless required for boot resilience.

Acknowledge these laws before writing any code.
```

---

## Sub-step 7P.0 — Discovery audit (read-only)

**Goal:** Inventory current deploy blockers. **Zero file changes.**

**Files to open in Cursor:**
- `docker-compose.yml`
- `Dockerfile`
- `src/config.py`
- `.env.example`
- `src/main.py`
- `src/worker/main.py`
- `src/core/health.py`
- `monitoring/prometheus.yml`
- `nginx/default.conf`

---

```
ROLE: Senior platform engineer — pre-implementation audit only.

OBJECTIVE: Sub-step 7P.0 — Production readiness discovery.
Do NOT modify any file. Produce a written report only.

Analyze and report:

1. DOCKER COMPOSE (dev)
   - List all services and which env vars are hardcoded in environment: blocks
   - Identify overrides that would block pointing .env at hosted services
   - Note depends_on chains that assume local db/redis/qdrant

2. SETTINGS / ENV GAP
   - Every field in src/config.py Settings class
   - Which are in .env.example vs missing
   - Which prometheus/grafana vars are used in monitoring/ but missing from .env.example

3. STARTUP HARD DEPENDENCIES
   - main.py lifespan: what runs at boot and what is already non-fatal
   - worker/main.py startup: what fails if Qdrant is unreachable
   - Would API start if only Postgres+Redis are up?

4. STORAGE
   - Current STORAGE_BACKEND default and prod implications
   - Whether api+worker need shared volume in prod

5. HEALTH ENDPOINT
   - What /health checks today
   - Recommendation: keep db+redis as hard; qdrant as separate /health/ai or optional

6. EXISTING CI
   - Is .github/workflows present?
   - pytest.ini and test entry points

7. OUTPUT (required sections)
   - Files to CREATE (path + purpose)
   - Files to MODIFY (path + what changes, append-only where possible)
   - Risks (ordered by severity)
   - Recommended sub-step order if anything differs from 7P.1–7P.8
   - Open questions for the human (hosted provider choices, VPS OS, domain/TLS)

Wait for explicit human approval before 7P.1.
```

**Validation:** Report exists in chat or `docs/deployment/audit-7p0.md` (optional). No code changes.

---

## Sub-step 7P.1 — Environment contract

**Goal:** Single env contract across dev Docker, prod Docker, and CI. No behavior change.

**Files to open:**
- `src/config.py`
- `.env.example`
- `monitoring/prometheus.yml`
- `monitoring/prometheus-entrypoint.sh`

---

```
ROLE: Senior platform engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7P.1 — Sync env contract for production.
Append-only to .env.example. Create .env.production.example. No runtime code changes.

LAWS: Platform ARCHITECTURE LAW applies. Do not modify docker-compose.yml in this step.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — Audit src/config.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
List every Settings field. Ensure .env.example has a documented entry for each
(non-secret placeholder). Group comments match existing slice style:
  # ── Existing ──
  # ── AI Providers ──
  # ── Platform / Production ──  (new group)

Add any MISSING vars found in monitoring/ or compose that Settings or prometheus reads:
  GRAFANA_CLOUD_REMOTE_WRITE_URL
  GRAFANA_ADMIN_PASSWORD (if grafana ever added locally)
  DEBUG, CORS_ORIGINS, STORAGE_BACKEND, R2_*, JWT_REFRESH_SECRET
  Keep placeholders — no real secrets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Create .env.production.example
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
New file at repo root. Template for VPS / hosted services.

Must include:
  DEBUG=false
  CORS_ORIGINS=["https://your-frontend.example.com"]

  DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DB?sslmode=require
  REDIS_URL=rediss://:TOKEN@HOST:6379/0
  ARQ_REDIS_URL=rediss://:TOKEN@HOST:6379/0

  QDRANT_URL=https://xxxx.cloud.qdrant.io
  QDRANT_API_KEY=

  STORAGE_BACKEND=r2
  R2_ENDPOINT=https://ACCOUNT_ID.r2.cloudflarestorage.com
  R2_ACCESS_KEY_ID=
  R2_SECRET_ACCESS_KEY=
  R2_BUCKET=dashnote-prod

  JWT_SECRET=generate-with-openssl-rand-hex-32
  JWT_REFRESH_SECRET=generate-with-openssl-rand-hex-32

  # LLM keys — at least one required for AI features
  GEMINI_API_KEY=
  NVIDIA_NIM_API_KEY=

  # Optional observability — deploy succeeds without these
  LANGFUSE_PUBLIC_KEY=
  LANGFUSE_SECRET_KEY=
  GRAFANA_CLOUD_REMOTE_WRITE_URL=
  GRAFANA_CLOUD_USER=
  GRAFANA_CLOUD_TOKEN=

Add header comment:
  # Copy to .env on VPS: cp .env.production.example .env
  # Never commit .env

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Document dependency tiers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Append a short section to docs/documentation/system.md (or create
docs/deployment/README.md if system.md is too crowded):

  - Hard vs soft vs optional dependencies (table from slice-platform.md)
  - Dev: docker compose up (full stack)
  - Prod: docker compose -f docker-compose.prod.yml up (VPS)

Do NOT add secrets. Do NOT change src/config.py unless a field is genuinely missing
and required for prod (append-only).

OUTPUT: Complete file contents for new/changed files. Zero truncation.
```

**Validation:**
```powershell
# Every Settings field appears in .env.example (manual spot-check or script)
python -c "from config import Settings; print('settings ok')"
# .env.production.example exists and is not in .gitignore
```

**Commit message:** `docs(platform): sync env contract and add .env.production.example`

---

## Sub-step 7P.2 — Production Docker Compose

**Goal:** New `docker-compose.prod.yml` for VPS. Local `docker-compose.yml` unchanged.

**Files to open:**
- `docker-compose.yml`
- `Dockerfile`
- `nginx/default.conf`
- `.env.production.example`

---

```
ROLE: Senior platform engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7P.2 — Add docker-compose.prod.yml for VPS deployment.
Local dev docker-compose.yml must behave identically after this change.

LAWS: Platform ARCHITECTURE LAW. Append-only to docker-compose.yml — at most add
comments clarifying "dev only". All prod services go in the NEW file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — Create docker-compose.prod.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Services:

  migrate:
    build: . (same Dockerfile)
    env_file: .env
    command: ["alembic", "upgrade", "head"]
    restart: "no"
    # No depends_on local db — DATABASE_URL comes from .env (hosted Postgres)

  api:
    build: . OR image: ${IMAGE:-dashnote-api:latest}  # support CI-pulled images
    env_file: .env
    environment:
      DEBUG: "false"
      # NO DATABASE_URL, REDIS_URL, QDRANT_URL overrides here
    volumes: []   # no local_storage — prod uses R2
    expose: ["8000"]   # not published — nginx fronts traffic
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s

  worker:
    build: . OR same image as api
    command: python -m arq src.worker.main.WorkerSettings
    env_file: .env
    environment:
      DEBUG: "false"
    volumes: []
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    depends_on:
      - api
    ports:
      - "80:80"
      # Document: add 443 + certs in 7P.5 runbook (Caddy/Certbot/Cloudflare)
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped

  prometheus:  (optional — comment "enable with --profile observability")
    Use profiles: [observability]
    Same image/config as dev prometheus
    env_file: .env
    scrape target: api:8000
  # No grafana on VPS — use Grafana Cloud

Use project name comment at top:
  # Production compose — requires .env with hosted service URLs
  # Usage: docker compose -f docker-compose.prod.yml up -d
  # Local dev: docker compose up -d  (default docker-compose.yml)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Dev compose clarity (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add comments above api/worker environment: blocks in docker-compose.yml:

  # Dev overrides — take precedence over .env for local service discovery.
  # Production uses docker-compose.prod.yml with env_file only.

Do NOT remove dev overrides.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Update docs/documentation/system.md Docker section
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Document both compose files and commands:

  # Local (full stack)
  docker compose up -d --build

  # Production (VPS — hosted db/redis/qdrant in .env)
  docker compose -f docker-compose.prod.yml run --rm migrate
  docker compose -f docker-compose.prod.yml up -d

OUTPUT: Complete docker-compose.prod.yml content. Minimal diff on docker-compose.yml.
```

**Validation — must pass both profiles:**
```powershell
# Local dev still works (unchanged behavior)
docker compose up -d --build
curl.exe -sS http://127.0.0.1/health

# Prod file parses (no need for hosted .env on dev machine)
docker compose -f docker-compose.prod.yml config
```

**Commit message:** `feat(platform): add docker-compose.prod.yml for VPS deployment`

---

## Sub-step 7P.3 — Non-fatal soft dependency boot

**Goal:** API and worker start when Qdrant (or LLM) is temporarily unreachable. Deploy not blocked.

**Files to open:**
- `src/main.py`
- `src/worker/main.py`
- `src/ai/retrieval/collection.py`

---

```
ROLE: Senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7P.3 — Make Qdrant collection bootstrap non-fatal at startup.
Mirror the existing checkpointer try/except pattern in main.py lifespan.

LAWS: Do not change Qdrant indexing logic. Do not remove ensure_*_collection calls.
Only wrap startup calls so failures log ERROR and continue.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/main.py lifespan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Where ensure_notes_collection / ensure_files_collection are called:

  if settings.qdrant_enabled:
      try:
          await ensure_notes_collection()
          await ensure_files_collection()
          logger.info("Qdrant collections ready")
      except Exception as e:
          logger.error(
              "Qdrant collection bootstrap failed — AI retrieval degraded",
              extra={"error": str(e)},
          )

Non-fatal — app continues to serve /health, /notes, etc.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/worker/main.py startup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Same try/except around Qdrant collection ensure in worker startup.

Worker still requires Redis (hard dependency for ARQ) — do not catch Redis connection
failures silently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Optional: GET /health/ai (only if trivial)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If adding a route is clean, add src/core/health_ai.py or extend health.py:

  GET /health/ai — probes Qdrant when qdrant_enabled; returns 200 degraded or 503
  Do NOT add Qdrant to main /health gate — deploy gate stays db+redis only.

Skip this task if it would touch too many files — document as 7P.6 instead.

OUTPUT: Minimal diff. Existing tests must pass.
```

**Validation:**
```powershell
python -m pytest tests/ -q

# Simulate Qdrant down — api should still start (dev):
docker compose stop qdrant
docker compose up -d api
curl.exe -sS http://127.0.0.1/health   # expect 200 if db+redis up
docker compose start qdrant
```

**Commit message:** `fix(platform): non-fatal Qdrant bootstrap at api and worker startup`

---

## Sub-step 7P.4 — Production storage contract

**Goal:** Document and validate R2 path for prod. Dev local storage unchanged.

**Files to open:**
- `src/core/storage/client.py`
- `.env.production.example`
- `src/config.py`

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Sub-step 7P.4 — Production object storage contract (R2).
No breaking changes to local dev STORAGE_BACKEND=local.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — Verify R2 code path
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read core/storage/client.py. Confirm api upload and worker download both use
get_storage() — no direct filesystem paths in worker automation tasks.

If any worker task reads LOCAL_STORAGE_PATH directly, fix to use get_storage()
(minimal change only).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Document in docs/deployment/storage.md (new, short)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - Why prod requires R2/S3 (no shared volume between api and worker on VPS)
  - Env vars checklist
  - Cloudflare R2 bucket CORS if frontend uploads directly (note: API uploads today)
  - Dev vs prod table

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — .env.production.example
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ensure STORAGE_BACKEND=r2 and all R2_* vars are present with comments.

Do NOT add new storage backends. Do NOT change default in config.py (local for dev).

OUTPUT: storage.md + any minimal worker fix if path bypass found.
```

**Validation:**
```powershell
# Local dev unchanged
docker compose up -d --build api worker
python -m pytest tests/files -q
```

**Commit message:** `docs(platform): production R2 storage contract`

---

## Sub-step 7P.5 — Deploy scripts & runbook

**Goal:** Repeatable deploy commands without CI yet. Human can deploy manually to VPS.

**Files to create:**
- `docs/deployment/runbook.md`
- `scripts/deploy/migrate.sh`
- `scripts/deploy/up.sh`
- `scripts/deploy/health-check.sh`

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Sub-step 7P.5 — Deployment runbook and shell scripts for VPS.
Bash scripts (VPS is Linux). PowerShell notes in runbook for local dev.

LAWS: Scripts must use docker compose -f docker-compose.prod.yml.
Never embed secrets in scripts — read from .env on VPS.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — docs/deployment/runbook.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sections:

  1. Prerequisites checklist
     - VPS (Ubuntu 22.04+), Docker + Compose plugin
     - Hosted Postgres, Redis, Qdrant Cloud, R2 bucket provisioned
     - DNS A record → VPS (or Cloudflare proxy)

  2. First-time VPS setup
     - git clone / copy compose files
     - cp .env.production.example .env && fill secrets
     - docker compose -f docker-compose.prod.yml build

  3. Deploy sequence (every release)
     - git pull OR docker pull IMAGE
     - ./scripts/deploy/migrate.sh
     - ./scripts/deploy/up.sh
     - ./scripts/deploy/health-check.sh

  4. Rollback
     - docker compose -f docker-compose.prod.yml pull PREVIOUS_TAG
     - re-run up.sh

  5. TLS options (decision doc — pick one)
     - Cloudflare SSL (flexible/full)
     - Caddy reverse proxy instead of nginx
     - Certbot + nginx

  6. Optional observability profile
     - docker compose -f docker-compose.prod.yml --profile observability up -d prometheus

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — scripts/deploy/*.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
migrate.sh:
  set -euo pipefail
  docker compose -f docker-compose.prod.yml run --rm migrate

up.sh:
  docker compose -f docker-compose.prod.yml up -d api
  wait for health (loop curl localhost/health via nginx or api)
  docker compose -f docker-compose.prod.yml up -d worker nginx
  optional: --profile observability

health-check.sh:
  curl -sf http://127.0.0.1/health | jq .
  exit non-zero if status != ok

Make executable in docs (chmod +x). Use LF line endings.

OUTPUT: Complete script and runbook contents.
```

**Validation:**
```powershell
docker compose -f docker-compose.prod.yml config
# Scripts run in dry documentation review — full VPS test is 7P.8 gate
```

**Commit message:** `docs(platform): VPS deploy runbook and scripts`

---

## Sub-step 7P.6 — Smoke test script

**Goal:** Post-deploy verification script (auth → upload → automation check).

**Files to open:**
- `scripts/e2e_agent_test.py` (reference pattern)
- `docs/user.md`

---

```
ROLE: Senior QA/platform engineer.

OBJECTIVE: Sub-step 7P.6 — Production smoke test script.
Callable against any base URL (default http://127.0.0.1).

Create scripts/smoke_prod.py (or extend existing e2e script with --base-url):

  1. GET /health — assert 200 and dependencies.database.reachable
  2. Register test user OR login via env SMOKE_EMAIL / SMOKE_PASSWORD
  3. POST /files/upload (small PDF fixture from tests/fixtures if exists)
  4. Poll GET /files/{id} for up to 90s — assert summary or tags populated
  5. Print PASS/FAIL per step; exit 1 on failure

Env vars (all optional for local):
  SMOKE_BASE_URL=https://api.example.com
  SMOKE_EMAIL=
  SMOKE_PASSWORD=

Document in docs/deployment/runbook.md under "Post-deploy smoke".

Do not commit real credentials. Reuse httpx/requests patterns from existing tests.

OUTPUT: Complete smoke_prod.py + runbook section.
```

**Validation:**
```powershell
# Against local stack
python scripts/smoke_prod.py
# Or: SMOKE_BASE_URL=http://127.0.0.1 python scripts/smoke_prod.py
```

**Commit message:** `feat(platform): production smoke test script`

---

## Sub-step 7P.7 — CI workflow (GitHub Actions)

**Goal:** PR checks — pytest + Docker build. No deploy, no VPS secrets.

**Prerequisite:** Repo on GitHub. Run only when ready for CI.

**Files to create:**
- `.github/workflows/ci.yml`

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Sub-step 7P.7 — GitHub Actions CI for pull requests.

LAWS: No production secrets in CI. No SSH deploy in this workflow.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — .github/workflows/ci.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
on: pull_request, push to main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r requirements/base.txt (or requirements.txt if that's the path)
      - pytest -q
        env:
          DATABASE_URL: sqlite+aiosqlite:///:memory: OR use pytest fixtures only
          JWT_SECRET: test-secret
          JWT_REFRESH_SECRET: test-refresh
          REDIS_ENABLED: false
          # Match conftest.py patterns — read tests/conftest.py first

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - checkout
      - docker build -t dashnote:ci .
      - optional: docker run --rm dashnote:ci python -c "from src.main import app"

Read tests/conftest.py and pytest.ini — CI env must match what tests expect.
If tests require Postgres service, add services: postgres to workflow.

Do NOT add deploy job here.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — README or docs/deployment/ci.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Short: what CI runs, how to fix local pytest before push.

OUTPUT: Complete workflow YAML.
```

**Validation:** Open PR or `act` locally if available. GitHub Actions green on main.

**Commit message:** `ci(platform): add GitHub Actions test and docker build workflow`

---

## Sub-step 7P.8 — CD workflow & production gate

**Goal:** Push image to registry, SSH deploy to VPS, run gate. **Run only when VPS and secrets exist.**

**Files to create:**
- `.github/workflows/deploy.yml`
- Update `docs/deployment/runbook.md` with GitHub Secrets table

---

```
ROLE: Senior platform engineer.

OBJECTIVE: Sub-step 7P.8 — CD pipeline and production gate.

LAWS:
  Deploy workflow triggers on: push tags v* OR workflow_dispatch only.
  Never auto-deploy every main push until explicitly desired.
  Secrets: VPS_HOST, VPS_USER, VPS_SSH_KEY, optional GHCR_TOKEN

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — .github/workflows/deploy.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
on:
  workflow_dispatch:
  push:
    tags: ['v*']

jobs:
  deploy:
    steps:
      1. build + push image to ghcr.io/ORG/dashnote:TAG
      2. SSH to VPS:
           cd /opt/dashnote
           export IMAGE=ghcr.io/...
           docker pull $IMAGE
           docker compose -f docker-compose.prod.yml run --rm migrate
           docker compose -f docker-compose.prod.yml up -d
      3. SSH: run scripts/deploy/health-check.sh
      4. optional: run smoke_prod.py against public URL

Use appleboy/ssh-action or native ssh with key from secrets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — docker-compose.prod.yml image override
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ensure api and worker accept:
  image: ${DASHNOTE_IMAGE:-}
  build: ... only when DASHNOTE_IMAGE unset

So VPS can pull CI image without rebuilding on server.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Production gate checklist in runbook
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gate (all must pass):

  [ ] curl https://api.example.com/health → 200
  [ ] python scripts/smoke_prod.py → PASS
  [ ] docker compose -f docker-compose.prod.yml ps — all healthy
  [ ] Worker logs: no crash loop
  [ ] Qdrant Cloud dashboard shows collections
  [ ] R2 bucket has objects after test upload

Only after gate: resume Slice 8+ feature work.

OUTPUT: deploy.yml + compose image override + runbook gate section.
```

**Validation — Production gate:**
```bash
# On VPS after first CD deploy
./scripts/deploy/health-check.sh
SMOKE_BASE_URL=https://api.yourdomain.com python scripts/smoke_prod.py
```

**Commit message:** `ci(platform): add CD deploy workflow and production gate`

---

## Slice Platform Complete — What Was Built

```
docker-compose.prod.yml          ← VPS: nginx, api, worker, migrate, optional prometheus
docker-compose.yml               ← unchanged dev stack (+ comments only)
.env.production.example          ← hosted service template
.env.example                     ← synced with config.py
docs/deployment/runbook.md       ← VPS setup + deploy + rollback + TLS
docs/deployment/storage.md       ← R2 contract
docs/deployment/ci.md            ← optional CI notes
scripts/deploy/migrate.sh
scripts/deploy/up.sh
scripts/deploy/health-check.sh
scripts/smoke_prod.py
.github/workflows/ci.yml
.github/workflows/deploy.yml
src/main.py                      ← non-fatal Qdrant boot (7P.3)
src/worker/main.py               ← non-fatal Qdrant boot (7P.3)
```

```
What is NOT in this slice (correct — later):
  ✗ Neo4j / GraphRAG (Slice 8)
  ✗ Multi-agent (Slice 9)
  ✗ Full usage dashboard (Slice 10)
  ✗ Worker autoscaling / model routing (Slice 11)
  ✗ Kubernetes / Terraform — single VPS is enough for now

What must NEVER break:
  docker compose up -d --build          ← full local dev stack
  curl http://127.0.0.1/health          ← 200 with local db+redis
  python -m pytest -q                   ← green
```

---

## Quick reference — compose commands

```powershell
# Local development (full stack — default)
docker compose up -d --build
docker compose ps
curl.exe -sS http://127.0.0.1/health

# Production (VPS — .env points at hosted services)
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml --profile observability up -d   # optional

# Validate prod compose file syntax (any machine)
docker compose -f docker-compose.prod.yml config
```

---

> **Next:** Slice 8 — GraphRAG with Neo4j (optional) **or** Slice 10 — Observability
> Start feature slices only after **7P.8 production gate** passes on real VPS.
