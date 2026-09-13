## Why

Hosted data plane (Supabase, Redis, Qdrant Cloud, R2) and an AWS t3.small (2 GB RAM / 30 GiB) with SSH access exist, but the API is not yet running on that box. There is no domain, so HTTPS A7 cannot close. Operators need a first-boot path: gitignored production env, thin prod compose only, HTTP health + `smoke_prod.py` against the VPS public IP — without claiming production-live or hire-ready.

## What Changes

- Operator first-boot of `docker-compose.prod.yml` on the t3.small (api + worker + nginx only) talking to already-provisioned hosted services.
- Document a clean, gitignored `.env.production` → VPS `.env` copy path (never commit secrets; keep `.env.production.example` as the template).
- Record HTTP-on-IP health and hard-gate smoke as **first-boot evidence** (partial A: A1 operator-confirmed; A4 HTTP-IP allowed). **A7 TLS, production-live, and job-search remain closed** until a domain exists.
- Lock 2 GB RAM topology in runbook / `production.md`: no local Postgres/Redis/Qdrant on the VPS; no Prometheus profile on first boot; swap recommended; frontend stays off this box.
- Close the 2026-09 “VPS A-gate deferred” window in blueprint8 / `goal.md` trackers: VPS work resumes as HTTP first-boot, not as hire-ready.
- No GraphRAG, no HITL/eval product changes, no sibling FE deploy (B7 still needs a domain).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Add a first-boot HTTP-on-IP gate distinct from HTTPS production-live; require thin-VPS compose on ≤2 GB (hosted data plane only); document gitignored `.env.production` operator path and t3.small topology (replace stale Oracle 8 GB assumption).
- `portfolio-baseline`: Allow recording HTTP first-boot / A1 confirmation in trackers without marking A7, production-live, or hire-ready complete.
- `blueprint8-ship-path`: End the local-only deferred VPS window; first-boot on the 2 GB AWS box is the next Alive step; TLS remains mandatory before any production-live claim.

## Impact

- **Docs / trackers:** `docs/deployment/runbook.md`, `docs/documentation/production.md`, `docs/documentation/blueprint8.md`, `docs/documentation/blueprint/goal.md` (and ship-plan pointer if the deferred-window text still contradicts).
- **Env contract:** `.env.production.example` comments for HTTP-first CORS / public IP; local `.env.production` stays gitignored (already covered by `.env.*`).
- **Ops:** Manual SSH first-boot using existing `scripts/deploy/*` and `scripts/smoke_prod.py`; GitHub CD HTTPS smoke not required to close this change.
- **Runtime:** Prod compose must not grow data-plane services; optional observability profile stays off first boot.
- **Out of scope:** Domain purchase, TLS/Caddy/Cloudflare Full Strict, B7 FE deploy, claiming A4 HTTPS / A7, Lite template, GraphRAG, multi-agent, app route changes.
