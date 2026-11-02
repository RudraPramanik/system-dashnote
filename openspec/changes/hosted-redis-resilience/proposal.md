## Why

Hosted production is down in a self-feeding loop: Upstash refuses commands ("temporarily rate-limited"), the global rate limiter turns that into HTTP 500 on every request (including `GET /health`), Docker keeps probing `/health` every 30s, and the ARQ worker exits-and-restarts tens of thousands of times against the same Redis. Operators now have Redis Cloud and Layerbase credentials; we need a durable provider layout, fail-open Redis client behavior, and a VPS env cutover so `api.aisystem.world` can recover without burning the next free tier the same way.

## What Changes

- Adopt **Redis Cloud** as the production Redis for both `REDIS_URL` (cache + app rate limits) and `ARQ_REDIS_URL` (ARQ queue) on the thin VPS — same database is allowed and preferred on the free Essentials plan (one free DB, real `BLPOP`).
- Treat **Layerbase** as optional/deferred for production always-on use: free hibernation (sleep after idle, mandatory weekly sleep share) conflicts with the Docker healthcheck and a long-lived worker. Document Solo/always-on as a later upgrade path, not the recovery cutover.
- Make the global (and auth) Redis rate limiters **fail open** on Redis errors (quota / connection / `ResponseError`): never turn Redis outage into an unhandled 500; optionally skip limiting for hard health paths so probes cannot amplify a Redis cliff.
- Update operator docs (runbook / system notes) for: stop-the-storm steps, VPS `.env` URL shapes (no secrets in git), cutover order (stop worker → patch env → recreate api/worker → prove health), and Redis Cloud inactivity / connection / ops-per-sec limits.
- **Out of scope for this change's hard gate:** repairing the separate Supabase tenant/user failure (still required for full `/health` green, tracked as ops follow-on). No worker package upgrade required for recovery.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Require fail-open Redis rate limiting under Redis errors; document Redis Cloud as the production Redis (cache + ARQ) cutover; document Layerbase free vs always-on tradeoffs; document VPS storm-stop and env alignment without embedding secrets.

## Impact

- Code: `src/core/security/rate_limit.py` (and any global dependency wiring); tests under `tests/core/` for fail-open behavior.
- Ops: VPS `/opt/dashnote/.env` (or deploy path `.env`) — set `REDIS_URL` / `ARQ_REDIS_URL` to Redis Cloud DSN; do not commit secrets; optional local `.env` notes for operators.
- Docs: `docs/deployment/runbook.md`, `docs/documentation/system.md` (hosted Redis layout).
- Runtime deps unchanged (still `redis` / ARQ over Redis protocol). No Momento / Vercel KV.
- Frontend unchanged. Postgres/Qdrant/R2 unchanged by this change.
