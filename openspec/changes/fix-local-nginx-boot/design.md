## Context

See proposal.md — Why. Today both Compose files mount the same `nginx/default.conf`, which includes a `listen 443 ssl` server that references `/etc/nginx/certs/origin.{crt,key}`. Nginx fails config load if those files are missing, so local nginx never binds `:80` even though local compose only publishes port 80 and does not mount `nginx/certs/`. Prod compose mounts certs and needs the SSL block for Cloudflare Full.

## Goals / Non-Goals

**Goals:**

- Local `docker compose up` starts nginx without any TLS files.
- `GET http://127.0.0.1/health` works on the developer path after recreate.
- Production nginx config path and SSL behavior stay identical for the VPS/hosted stack.

**Non-Goals:**

- Changing frontend env vars or hosted `NEXT_PUBLIC_API_BASE_URL`.
- Committing real or placeholder certs into git.
- Fixing host port `:8000` conflicts or other unrelated Compose issues.
- Altering Cloudflare, Terraform, or deploy workflow triggers.

## Decisions

### 1. Split nginx configs by Compose file (chosen)

- Add `nginx/local.conf`: HTTP `:80` only (same upstream / rate-limit / `/ai/` timeouts as today’s port-80 server).
- Keep `nginx/default.conf` as the production config (HTTP `:80` + SSL `:443` with existing cert paths).
- Change `docker-compose.yml` nginx volume to mount `./nginx/local.conf` → `/etc/nginx/conf.d/default.conf`.
- Leave `docker-compose.prod.yml` volumes unchanged (`default.conf` + `nginx/certs`).

**Why over generating local self-signed certs:** avoids openssl as a local prerequisite, avoids mounting empty/missing cert dirs, and keeps “local = HTTP” vs “prod = Full TLS” explicit.

**Why over stripping SSL from `default.conf`:** would break hosted A7 unless prod gained another include; splitting keeps prod file byte-stable for the SSL server block.

**Alternatives considered:**

| Option | Rejected because |
|--------|------------------|
| Generate gitignored certs in a setup script | Extra step; still couples local to TLS; easy to skip |
| `ssl_certificate` optional via envsubst | More moving parts; easy to misconfigure prod |
| Single conf with only `:80` and TLS elsewhere | Same as split, but renaming prod path would touch prod compose |

### 2. Keep proxy behavior parity on `:80`

Local conf MUST preserve: Docker embedded DNS resolver + `api:8000 resolve`, `limit_req` zones, `/ai/` `proxy_read_timeout 180s`, and standard proxy headers — so SSE and CORS behavior match what developers already rely on.

### 3. Docs: one short note, not a new runbook chapter

Mention in the existing edge/local docs that local Compose uses `nginx/local.conf` (HTTP only) and prod uses `nginx/default.conf` + certs. Do not change A7 runbook TLS generation steps.

## Risks / Trade-offs

- **[Drift between local and prod `:80` blocks]** → Mitigation: copy the current port-80 server into `local.conf` once; tasks include a checklist to keep proxy timeouts/headers aligned when either file changes later.
- **[Someone edits only `default.conf` and assumes local picks it up]** → Mitigation: document the split; local compose mount makes the wrong file obvious in `docker compose config`.
- **[VPS accidentally uses local compose]** → Already forbidden by production-platform; this change does not encourage it.

## Migration Plan

1. Add `nginx/local.conf`, retarget local compose mount.
2. Recreate local nginx: `docker compose up -d --force-recreate nginx` (or full `up -d`).
3. Verify `GET http://127.0.0.1/health` and that nginx is not Restarting.
4. Hosted: no deploy required if `default.conf` and prod compose are untouched; if a no-op touch occurs, normal recreate nginx on VPS with existing certs.

Rollback: restore local compose volume to `default.conf` (returns to broken local without certs — only useful if local.conf itself is wrong).
