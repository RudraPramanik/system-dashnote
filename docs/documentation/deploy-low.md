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