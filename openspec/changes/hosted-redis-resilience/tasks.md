## 1. Fail-open rate limiting

- [x] 1.1 Update `RateLimiter.check` so Redis errors (connection, timeout, provider quota/`ResponseError`) fail open: log warning, allow the request (no unhandled 500)
- [x] 1.2 Skip global rate limiting for `GET /health` and `GET /health/ai` (or equivalent dependency guard) so Docker probes never depend on rate-limit counters
- [x] 1.3 Add/adjust unit tests covering fail-open on Redis error and continued 429 when counters succeed

## 2. Docs and env contract

- [x] 2.1 Document Redis Cloud cutover in `docs/deployment/runbook.md`: stop worker → set `REDIS_URL` + `ARQ_REDIS_URL` → recreate api/worker → prove; note free-tier connection/ops caps; no secrets in git
- [x] 2.2 Update `docs/documentation/system.md` hosted Redis line to Redis Cloud for cache+ARQ; Layerbase Free deferred; Momento/Vercel KV not for ARQ
- [x] 2.3 Align `.env.production.example` comments with Redis Cloud DSN shape and “same host OK for ARQ”; do not add unused `LAYERBASE_*` / `REDIS_PUBLIC_ENDPOINT` runtime settings

## 3. Operator VPS cutover (manual; no secret commits)

- [x] 3.1 On VPS: `docker compose -f docker-compose.prod.yml stop worker` to halt the restart storm
- [x] 3.2 Patch VPS `.env` only: set both `REDIS_URL` and `ARQ_REDIS_URL` to the Redis Cloud DSN (verify `redis://` vs `rediss://` with a one-shot PING); leave Layerbase off the VPS for this cutover
- [x] 3.3 Recreate/restart `api` (+ deploy fail-open image when ready) then `worker`; confirm worker restart count stabilizes and `/health` no longer 500s from Redis rate-limit errors
- [x] 3.4 Cross-note: if `/health` still fails after Redis recovers, diagnose Supabase tenant separately (out of code scope for this change)

## 4. Validation

- [x] 4.1 Run targeted pytest for rate-limit fail-open
- [x] 4.2 After VPS cutover: `GET https://api.aisystem.world/health` is not 500 from Redis limiter; soft-check worker stays Up
