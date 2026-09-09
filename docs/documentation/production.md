# Platform slice (7P) — tracker



> **AI:** Read this before any platform/deploy work. Detailed prompts live in `docs/documentation/blueprint/slice-platform.md`. Architecture laws in `docs/documentation/deploy-low.md`. App behavior in `system.md` + `ai.md`.
>
> **Locked path:** [`blueprint8.md`](blueprint8.md) (Alive + Tier 0/1/2). **Slice 8X detail (deploy-first):** After **7P.0–7P.3**, follow [`blueprint/slice8_X.md`](blueprint/slice8_X.md). Chosen: [`slice8_ci.md`](blueprint/slice8_ci.md) (7P.7) → **7P.4–7P.6 + 7P.8** → frontend → [`slice8_eval.md`](blueprint/slice8_eval.md) → [`slice8_hitl.md`](blueprint/slice8_hitl.md). Do not start evals/HITL before 7P.8 on the chosen path.



## Goal



Ship production on **hosted data plane + thin VPS compute** without breaking local `docker compose up`.



| Runs on VPS | Hosted (not on VPS) |

|-------------|---------------------|

| api, worker, migrate, nginx (HTTP :80 first-boot; TLS later). Prometheus **off** on 2 GB first-boot | Supabase, Redis (one or two hosts), Qdrant Cloud, R2, Grafana Cloud |



---



## Step checklist



| Step | Task | Status | Key outputs |

|------|------|--------|-------------|

| 7P.0 | Discovery audit | ✅ done | Chat report — blockers identified |

| pre-7P.1 | Micro: soft Qdrant boot + gitignore | ✅ done | `main.py`, `worker/main.py`, `.gitignore` |

| 7P.1 | Env contract | ✅ done | `.env.example`, `.env.production.example`, `system.md` tier table |

| 7P.2 | Prod compose | ✅ done | `docker-compose.prod.yml` |

| 7P.3 | Soft dependency boot | ✅ done | Qdrant try/except in `main.py`, `worker/main.py` |

| 7P.4 | Storage contract | ✅ done | `docs/deployment/storage.md`; R2 in `.env.production.example`; dev stays `local` + volume |

| 7P.5 | Deploy scripts + runbook | ✅ done | `scripts/deploy/*`, `docs/deployment/runbook.md` |

| 7P.6 | Health + smoke | ✅ done | `scripts/smoke_prod.py` hard gate; `GET /health/ai` soft Qdrant probe |

| 7P.7 | CI (PR) | ✅ done | `.github/workflows/ci.yml` |

| 7P.8 | CD + VPS gate | ✅ done | `.github/workflows/deploy.yml` (tag `v*` / `workflow_dispatch`); runbook CD + gate checklist; live VPS proof still required to claim production-live |



**Gate:** HTTP first-boot on the t3.small does **not** authorize GraphRAG / multi-agent. Claim production-live only after HTTPS A4/A7 smoke. GitHub CD HTTPS is not required to close first-boot.

**Exception (Slice 8X, chosen / deploy-first):** **7P.7 CI** may run **before** 7P.8; eval harness and HITL are deferred until **after** 7P.8 — see [`blueprint/slice8_X.md`](blueprint/slice8_X.md). (Alternate AI-depth-first path may still run evals/HITL before 7P.8.)



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

| **Hard** | Postgres (Supabase), Redis (`REDIS_URL`; `ARQ_REDIS_URL` MAY share the same host if BLPOP works) | `/health` must be 200 |

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

| VPS | **AWS t3.small** (~2 vCPU, **2 GB RAM**, 30 GiB disk) — thin compute only | — |

| TLS | First-boot: nginx **HTTP :80** on public IPv4 (no domain). Later: Cloudflare Full Strict / Caddy / Certbot → `api.<domain>` (A7) | — |

| Embeddings | Gemini `gemini/gemini-embedding-2` | `GEMINI_API_KEY` |

| LLM / agent | NVIDIA NIM `nvidia_nim/...` | `NVIDIA_NIM_API_KEY`, `LLM_MAX_RETRIES=4`, etc. |

| Metrics | Slim prometheus → **Grafana Cloud** remote_write | `GRAFANA_CLOUD_REMOTE_WRITE_URL`, `GRAFANA_CLOUD_USER`, `GRAFANA_CLOUD_TOKEN` |

| CORS | No `*` in prod (including HTTP-IP first-boot) | `CORS_ORIGINS` = local FE origins until `https://app.<domain>` exists |



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
| `scripts/smoke_prod.py` | 7P.6 — lean hard-gate smoke |

| `.github/workflows/ci.yml` | 7P.7 — PR pytest + docker build |
| `.github/workflows/deploy.yml` | 7P.8 — GHCR push + SSH deploy + smoke |



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



### 7P.3 ✅

- Qdrant collection bootstrap non-fatal at API and worker startup (try/except mirrors checkpointer pattern).

- `GET /health` unchanged — db + redis only; `/health/ai` added in 7P.6 (soft).



### 7P.4 ✅

- `docs/deployment/storage.md` + R2 contract in `.env.production.example`; api/worker use `get_storage()`.



### 7P.5 ✅

- `docs/deployment/runbook.md` — prerequisites, first-time setup, release sequence, rollback, TLS options (decision only), observability profile.

- `scripts/deploy/{migrate,up,health-check}.sh` — always `-f docker-compose.prod.yml`; no secrets in scripts; LF via `.gitattributes`.



### 7P.6 ✅

- `scripts/smoke_prod.py` — hard gate: `/health` + auth + notebook/note create; soft AI via `--with-ai` / `SMOKE_SOFT_AI=1`.

- `GET /health/ai` — soft Qdrant probe; never part of hard `/health` or default smoke exit.

- Runbook “Post-deploy smoke” section documents local and production base URLs.



### 7P.8 ✅

- `.github/workflows/deploy.yml` — `workflow_dispatch` + `v*` tags only; GHCR build/push; SSH migrate → up → health-check; runner `smoke_prod.py` hard gate.

- `docker-compose.prod.yml` — `IMAGE=` registry override documented (unchanged env name).

- Runbook §8 — GitHub Secrets, GHCR pull notes, production gate checklist.



---



## Quick commands



```powershell

# Local dev (unchanged)

docker compose up -d --build

curl.exe -sS http://127.0.0.1/health



# Prod (VPS — copy .env.production.example → .env first; bash scripts)

# chmod +x scripts/deploy/*.sh

# ./scripts/deploy/migrate.sh

# ./scripts/deploy/up.sh

# ./scripts/deploy/health-check.sh

# python scripts/smoke_prod.py
# SMOKE_BASE_URL=https://api.example.com python scripts/smoke_prod.py

docker compose -f docker-compose.prod.yml --profile observability up -d prometheus   # optional metrics



# Validate prod compose parses locally

docker compose -f docker-compose.prod.yml config



# Tests (must pass before CD)

python -m pytest -q

```


