## Context

See proposal.md — Why. Live failure mode: Upstash command ban → uncaught `redis.incr` in global rate limiter → HTTP 500 on `/health` → Docker healthcheck every 30s → worker `restart: unless-stopped` after ARQ ping failure. Operators now hold Redis Cloud and Layerbase credentials locally; VPS `.env` still points both Redis roles at Upstash.

App contracts (unchanged):
- `REDIS_URL` — cache, auth blacklist/refresh helpers, global/auth rate limits (`INCR`/`EXPIRE`/`PING`)
- `ARQ_REDIS_URL` — ARQ lists + blocking pop (falls back to `REDIS_URL` when empty)

## Goals / Non-Goals

**Goals:**
- Choose the most efficient free/always-on Redis layout for this thin VPS.
- Fail-open rate limiting so Redis provider cliffs cannot 500 the entire API.
- Document exact VPS cutover (stop storm → patch env → recreate → prove) without committing secrets.
- Clarify idle/"sleep" myths so we do not invent extra health pings.

**Non-Goals:**
- Fixing Supabase tenant/user (separate ops; still required for full hard health green).
- Migrating to Momento or Vercel KV.
- Paying for Layerbase Solo in this change (document only).
- Changing ARQ worker business tasks or upgrading ARQ as the recovery lever.
- Splitting cache and ARQ onto two free Redis Cloud DBs (free plan allows one DB).

## Decisions

### D1 — Production cutover: Redis Cloud for both `REDIS_URL` and `ARQ_REDIS_URL`

**Choice:** One Redis Cloud database; set both env vars to the same DSN.

**Why:** Free Essentials is real Redis (`BLPOP` works). One free DB per account. Same-host for cache + ARQ matches runbook ("MAY use the same host if BLPOP works") and avoids Layerbase free hibernation fighting the worker + healthcheck. Simplest ops for a 2 GB VPS.

**URL shape (no secrets in git):**
```text
REDIS_URL=redis://default:<PASSWORD>@<host>.db.redis.io:<port>
ARQ_REDIS_URL=redis://default:<PASSWORD>@<host>.db.redis.io:<port>
```
Use `rediss://` only if the provider requires TLS on that endpoint; Redis Cloud public endpoints often use `redis://` on the published port — verify with a one-shot `PING` from the VPS before recreate.

**Do not wire into settings as new vars:** `REDIS_DATABASE`, `REDIS_PUBLIC_ENDPOINT`, `REDIS_ENDPOINT_KEY`, `LAYERBASE_*` are operator notes only. Runtime still reads `REDIS_URL` / `ARQ_REDIS_URL`.

**Alternatives considered:**
- Layerbase Free for both → rejected: sleeps after ~15 min idle; free plan expects ~25% weekly sleep; worker + 30s healthcheck keep it awake forever.
- Redis Cloud ARQ + Layerbase Free cache → rejected for recovery: adds complexity; cache path still hits health/rate-limit continuously → same sleep conflict.
- Stay on Upstash → rejected until/unless quota clears; already proven storm amplifier.
- Momento / Vercel KV → rejected: no ARQ `BLPOP` (Momento) / product sunset (Vercel KV → Upstash).

### D2 — No special "14s sleep" health keep-alive

**Clarifications:**
- Redis Cloud does **not** sleep for ~14 seconds. The free-plan risk called out in comparisons is **~14 days inactive** deletion — normal `/health` every 30s while the stack is up already counts as activity. No extra keep-alive job.
- Layerbase Free wake is ~**1–5 seconds** after hibernation (not a 14s timer). Avoid free Layerbase for always-on prod rather than pinging it harder.

**Efficient stance:** Keep existing Compose healthcheck. Fix fail-open limiter. Do not add a second Redis ping loop.

### D3 — Fail-open rate limiter

**Choice:** Wrap Redis counter/`expire`/`ttl` in `RateLimiter.check` with try/except; on Redis errors, log a warning and return (allow request). Prefer also skipping the global limiter for `GET /health` and `GET /health/ai` so probes never depend on rate-limit keys.

**Why:** Hard health must report Postgres/Redis readiness, not die before those checks. Fail-closed 500 is what created the storm.

**Alternatives:** Fail closed with 503 — clearer signal, but still fails Docker healthcheck and keeps restart pressure; fail open is better for recovery and demos.

### D4 — Layerbase credentials: keep local, defer production

Store Layerbase connection string in local operator notes if desired. Do **not** set it on the VPS for this cutover. Revisit if Solo always-on is purchased or if a true idle-tolerant cache split is designed later.

### D5 — Storm stop before cutover

```text
1. ssh VPS
2. docker compose -f docker-compose.prod.yml stop worker
3. Patch .env REDIS_URL + ARQ_REDIS_URL → Redis Cloud DSN
4. docker compose -f docker-compose.prod.yml up -d api worker
   (or recreate after pull if shipping fail-open image)
5. curl /health — Redis dependency should ping; Postgres may still fail separately
6. Prove ARQ: worker stays Up without restart storm; enqueue/embed soft check optional
```

Ship fail-open code via normal image/CD when possible; env cutover alone stops Redis 500s **only if** Redis answers — if old image still fail-closes on other Redis errors, prioritize the code fix before heavy traffic.

## Risks / Trade-offs

- [Redis Cloud 30 connections / 100 ops/sec] → Keep pools small; never leave worker crash-looping; fail-open reduces probe amplification.
- [Redis Cloud 30 MB] → Fine for ARQ + rate-limit keys; do not store large blobs in Redis.
- [Single DB for cache + queue] → Key namespace collision low (ARQ vs `rate_limit:` prefixes); acceptable on free tier.
- [Postgres still broken] → `/health` may stay 503 until Supabase tenant is fixed; Redis cutover alone is not "production-live".
- [Secrets in chat / local `.env`] → Rotate if exposed; never commit; scrub `LAYERBASE_API_KEY` from git history if accidentally committed.
- [Layerbase unused after signup] → Acceptable; better than wrong topology.

## Migration Plan

1. Implement fail-open limiter + tests; update runbook/system Redis section.
2. Operator: stop worker on VPS; set Redis Cloud DSNs; restart api/worker.
3. Validate: Redis PING via `/health` dependencies when DB OK; worker restart count stable.
4. Rollback: point URLs back to previous Redis only if new provider is unreachable; prefer fixing DSN over returning to banned Upstash.

## Open Questions

- Whether Redis Cloud endpoint requires `redis://` vs `rediss://` for this specific database (verify once with `redis-cli` / short Python ping from VPS).
- Postgres recovery timeline (out of this change’s implementation tasks beyond a runbook cross-note).
