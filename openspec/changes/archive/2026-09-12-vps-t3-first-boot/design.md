## Context

See `proposal.md` for why. Scripts, `docker-compose.prod.yml`, `.env.production.example`, and `scripts/smoke_prod.py` already exist. `tier0-job-gate` still blocks A7 on a missing prod URL. Hosted services and SSH are available; there is no domain. `production.md` still describes Oracle ~8 GB, which does not match the AWS t3.small (2 GB / 30 GiB). `.env.*` is already gitignored except the two example files.

This change is mostly operator path + tracker honesty. App routes stay unchanged. Chat and agent stay separate.

## Goals / Non-Goals

**Goals:**
- A repeatable SSH first-boot that fits 2 GB RAM.
- HTTP-on-IP hard health + smoke as the acceptance bar.
- Env secrets only in gitignored files / VPS `.env`.
- Docs and `goal.md` match that bar (A1 yes; A7 / hire-ready no).

**Non-Goals:**
- Domain, certificates, Cloudflare Full Strict, or Caddy.
- Enabling GitHub CD as the only way to boot (manual first-boot is enough).
- Putting frontend, Prometheus, Postgres, Redis, or Qdrant on the t3.small.
- Changing FastAPI routes, HITL, evals, or RAG behavior.
- Claiming production-live after HTTP smoke.

## Decisions

### 1. HTTP public IP is the first-boot URL

Use `http://<vps-ipv4>/health` and `SMOKE_BASE_URL=http://<vps-ipv4>`. Nginx already publishes `:80` only.

Alternatives: wait for a domain (blocks all progress); nip.io / sslip.io (extra DNS magic, still not A7); SSH tunnel only (does not prove a public edge).

TLS options in the runbook stay decision docs. A later change wires one of them after a domain exists.

### 2. Manual SSH first-boot; CD is optional

First-boot: copy env, `migrate.sh` → `up.sh` → `health-check.sh` → laptop `smoke_prod.py` against the public IP.

Do not require `deploy.yml` to succeed this change. CD may later use `SMOKE_BASE_URL=http://<vps-ip>` (already allowed in the runbook) once GHCR + GitHub Secrets exist.

### 3. Prefer pulling an image; on-box build only with swap

A Python image `docker compose build` on 2 GB often OOMs.

Preferred: set `IMAGE=` to a GHCR (or local-built-and-copied) tag and `docker pull`. Fallback: 1–2 GiB swap, then build on the VPS. 30 GiB disk is enough either way.

Do not add data-plane services to prod compose to “simplify.” That is the OOM path.

### 4. Gitignored `.env.production` → VPS `.env`

Operator fills `.env.production` locally from `.env.production.example`, then copies to VPS `.env` (compose `env_file`). No new committed secret file. Comments on the example: HTTP-first, `CORS_ORIGINS` never `*`, `STORAGE_BACKEND=r2`, hosted URLs.

`REDIS_URL` and `ARQ_REDIS_URL` may point at the same Redis if it supports blocking pop; two vendors are not required for first-boot. Use the Supabase URL that actually reaches the VPS (session pooler vs direct; `ssl=require`).

### 5. AWS edge: open 80, keep 8000 internal

Security group: SSH (22) from the operator; HTTP 80 from the operator (and later the world if a demo is needed). Do not publish api `:8000`. Do not open 443 until TLS exists.

CORS lists browser origins (local FE). The API’s own IP is not a CORS origin. Do not add `*` to make IP demos “easier.”

### 6. Tracker language

- A1: complete (operator-confirmed hosted plane).
- A4: note local PASS + HTTP-IP first-boot PASS when recorded; HTTPS still required.
- A7 / B7 / D live links / job search: remain open.
- `blueprint8.md` active window: VPS resumed as HTTP first-boot; local Tier 1 is done, not a hire waiver.
- Replace Oracle 8 GB topology with t3.small 2 GB thin compute.

## Risks / Trade-offs

- **[Risk] HTTP on a public IP is plaintext** → Mitigation: treat as operator proof only; do not advertise as the stranger demo; close TLS as soon as a domain exists; avoid putting extra secrets in smoke traffic beyond ephemeral register.
- **[Risk] OOM on api+worker or during image build** → Mitigation: swap; no Prometheus; no local data plane; prefer pull over build; watch `docker stats`.
- **[Risk] Hosted URLs blocked from AWS (IPv6-only, IP allowlists, wrong pooler port)** → Mitigation: from the VPS, test TCP/TLS to Postgres/Redis/Qdrant/R2 before `up`; adjust pooler/SSL in env, not app code.
- **[Risk] Trackers get marked production-live after `/health` on IP** → Mitigation: explicit first-boot vs A7 wording in runbook and `goal.md`.
- **[Risk] Smoke from laptop cannot reach port 80** → Mitigation: security group / ufw allow operator IP; fall back to `smoke_prod.py` on the VPS against `http://127.0.0.1` plus an external `curl` to the public IP for A-edge proof.

## Migration Plan

1. Fill gitignored `.env.production`; scp to VPS as `.env`.
2. Install Docker Engine + Compose plugin if missing; add swap if build or runtime is tight.
3. Open SG/ufw for 22 and 80; clone or sync repo files (`docker-compose.prod.yml`, `nginx/`, `scripts/deploy/`).
4. `IMAGE=` pull **or** swap + build; `./scripts/deploy/migrate.sh`; `./scripts/deploy/up.sh`; `./scripts/deploy/health-check.sh`.
5. From laptop: `curl http://<ipv4>/health` then `SMOKE_BASE_URL=http://<ipv4> python scripts/smoke_prod.py`.
6. Update `goal.md` / `production.md` / blueprint8 window text; leave A7 unchecked.

Rollback: `docker compose -f docker-compose.prod.yml down`. Hosted data is unchanged. No schema rollback unless a new migration was applied (this change should not add Alembic).

## Open Questions

- Whether GHCR pull is already authenticated on the VPS (affects image source, not the HTTP gate).
- Whether `REDIS_URL` and `ARQ_REDIS_URL` are one instance or two (operator env; both valid).
- When a domain will be bought (starts the TLS follow-up; not this change).
