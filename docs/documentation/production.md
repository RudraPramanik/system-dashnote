# Platform slice (7P) — tracker

> **AI:** Read this before any platform/deploy work. Detailed prompts live in `docs/documentation/blueprint/slice-platform.md`. Architecture laws in `docs/documentation/deploy-low.md`. App behavior in `system.md` + `ai.md`.

## Goal

Ship production on **hosted data plane + thin VPS compute** without breaking local `docker compose up`.

| Runs on VPS | Hosted (not on VPS) |
|-------------|---------------------|
| api, worker, migrate, nginx (TLS via Caddy in 7P.5), optional slim prometheus | Supabase, Upstash, Redis Cloud, Qdrant Cloud, R2, Grafana Cloud |

---

## Step checklist

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 7P.0 | Discovery audit | ✅ done | Chat report — blockers identified |
| pre-7P.1 | Micro: soft Qdrant boot + gitignore | ✅ done | `main.py`, `worker/main.py`, `.gitignore` |
| 7P.1 | Env contract | ✅ done | `.env.example`, `.env.production.example`, `system.md` tier table |
| 7P.2 | Prod compose | ✅ done | `docker-compose.prod.yml` |
| 7P.3 | Soft dependency boot | ✅ done early | Qdrant try/except (was planned here) |
| 7P.4 | Storage contract | ⬜ | R2 docs; dev stays `local` + volume |
| 7P.5 | Deploy scripts + runbook | ⬜ | `scripts/deploy/*`, `docs/deployment/runbook.md` |
| 7P.6 | Health + smoke | ⬜ | `scripts/smoke_prod.py`, optional `/health/ai` |
| 7P.7 | CI (PR) | ⬜ | `.github/workflows/ci.yml` |
| 7P.8 | CD + VPS gate | ⬜ | `.github/workflows/deploy.yml`, real deploy |

**Gate:** Resume feature slices (8+) only after **7P.8** passes on Oracle VPS.

---

## Laws (do not break)

1. **`docker-compose.yml`** — full local dev stack; keep `db` / `redis` / `qdrant` hostnames in `environment:` overrides.
2. **`docker-compose.prod.yml`** — new file only; **no** db, redis, qdrant; **no** `DATABASE_URL` / `REDIS_URL` / `QDRANT_URL` in compose `environment:`.
3. **`src/config.py`** — single source of truth for env var names.
4. **One `Dockerfile`** — api, worker, migrate share it.
5. **Dev storage** — `STORAGE_BACKEND=local` + `local_storage` volume unchanged.
6. **Prod storage** — `STORAGE_BACKEND=r2`; no shared volume between api/worker.
7. **Soft deps** — Qdrant + LLM missing must not block boot; Postgres + Redis are hard (`GET /health`).

---

## Dependency tiers

| Tier | Services | Boot / deploy |
|------|----------|---------------|
| **Hard** | Postgres (Supabase), Redis (Upstash + Redis Cloud) | `/health` must be 200 |
| **Soft** | Qdrant Cloud, LLM keys | Boot OK; AI/indexing degrades |
| **Optional** | Langfuse, Grafana remote_write | Never block CD |

---

## Production topology (human-approved)

| Concern | Production choice | Env vars |
|---------|-------------------|----------|
| Postgres | Supabase pooler **:6543** | `DATABASE_URL` (`postgresql+asyncpg://...?ssl=require`) |
| App cache / rate limit | **Upstash** | `REDIS_URL` → DB `/0` only |
| ARQ worker queue | **Redis Cloud** (blocking `BLPOP`) | `ARQ_REDIS_URL` → separate host, DB `/0` |
| Vectors | **Qdrant Cloud**, dim **3072** | `QDRANT_URL`, `QDRANT_API_KEY` |
| Files | **Cloudflare R2** | `STORAGE_BACKEND=r2`, `R2_*` |
| VPS | **Oracle Ampere A1** (~2 vCPU, 8 GB for compose) | — |
| TLS | **Cloudflare** (Full Strict) → **Caddy** → api `:8000` | `api.yourdomain.com` |
| Embeddings | Gemini `gemini/gemini-embedding-2` | `GEMINI_API_KEY` |
| LLM / agent | NVIDIA NIM `nvidia_nim/...` | `NVIDIA_NIM_API_KEY`, `LLM_MAX_RETRIES=4`, etc. |
| Metrics | Slim prometheus → **Grafana Cloud** remote_write | `GRAFANA_CLOUD_REMOTE_WRITE_URL`, `GRAFANA_CLOUD_USER`, `GRAFANA_CLOUD_TOKEN` |
| CORS | No `*` in prod | `CORS_ORIGINS=["http://localhost:3000","https://app.yourdomain.com"]` |

**Dev:** compose forces local URLs (`db`, `redis`, `qdrant`) — intentional; `.env` hosted URLs are overridden in dev.

---

## Compose profiles

| File | When | Services |
|------|------|----------|
| `docker-compose.yml` | Local dev | `db`, `redis`, `qdrant`, `api`, `worker`, `nginx`, `prometheus`, `migrate` |
| `docker-compose.prod.yml` | VPS | `api`, `worker`, `nginx`, `migrate`; optional `prometheus` with `--profile observability` |

**Prod compose details (7P.2):**

- `env_file: .env` for all app services; only safe override in compose is `DEBUG=false`.
- `api` exposes `:8000` internally (not published); `nginx` publishes `:80`.
- No `local_storage` volume — files via R2 (`STORAGE_BACKEND=r2`).
- `IMAGE` env var (default `dashnote-api:latest`) for CI-pulled images; `build: .` still defined for local builds.
- `worker` starts after `api` healthcheck passes.
- Run migrations before `up`: `docker compose -f docker-compose.prod.yml run --rm migrate`.

---

## File map (platform)

| Path | Role |
|------|------|
| `docker-compose.yml` | Local dev only — do not strip services |
| `docker-compose.prod.yml` | VPS profile — nginx, api, worker, migrate, optional prometheus |
| `.env.example` | All `Settings` fields (7P.1) |
| `.env.production.example` | Hosted template for VPS `.env` (7P.1) |
| `src/config.py` | Settings source of truth |
| `src/main.py` | API lifespan; Qdrant soft boot ✅ |
| `src/worker/main.py` | Worker startup; Qdrant soft boot ✅ |
| `src/core/health.py` | Hard: db + redis |
| `nginx/default.conf` | Dev + prod proxy to `api:8000`; TLS in 7P.5 |
| `monitoring/prometheus.yml` | Scrape + Grafana Cloud remote_write |
| `scripts/deploy/*` | 7P.5 — migrate, up, health-check |
| `.github/workflows/*` | 7P.7 / 7P.8 |

---

## Step log (update after each sub-step)

### pre-7P.1 micro ✅
- Wrapped Qdrant collection bootstrap in try/except (`main.py`, `worker/main.py`).
- `.gitignore`: added `!.env.production.example`.

### 7P.1 ✅
- Synced `.env.example` ↔ all 59 `Settings` fields; added `# ── Platform / Production ──` group.
- Created `.env.production.example` (hosted URLs, R2, JWT, optional observability).
- Appended dependency tier table to `system.md`.

### 7P.2 ✅
- Created `docker-compose.prod.yml`: migrate, api (healthcheck, expose only), worker, nginx, optional prometheus (`observability` profile).
- Dev compose: append-only comments on `api`/`worker` `environment:` blocks clarifying dev overrides.
- Updated `system.md` Docker section with both compose files and prod commands.

---

## Quick commands

```powershell
# Local dev (unchanged)
docker compose up -d --build
curl.exe -sS http://127.0.0.1/health

# Prod (VPS — copy .env.production.example → .env first)
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml --profile observability up -d   # optional metrics

# Validate prod compose parses locally (no hosted .env required for config)
docker compose -f docker-compose.prod.yml config

# Tests (must pass before CD)
python -m pytest -q
```
