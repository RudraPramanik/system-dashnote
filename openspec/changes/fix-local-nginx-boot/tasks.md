## 1. Local nginx config

- [x] 1.1 Add `nginx/local.conf` with the current HTTP `:80` server only (resolver, `api_upstream`, rate limit, `/ai/` 180s timeouts, proxy headers) — no `listen 443 ssl` and no cert paths
- [x] 1.2 Confirm `nginx/default.conf` still contains the production `:80` + `:443` SSL server blocks unchanged

## 2. Compose wiring

- [x] 2.1 Point `docker-compose.yml` nginx volume at `./nginx/local.conf:/etc/nginx/conf.d/default.conf:ro`
- [x] 2.2 Confirm `docker-compose.prod.yml` still mounts `./nginx/default.conf` and `./nginx/certs` with ports `80` and `443` (no edits unless a typo fix is required)

## 3. Docs

- [x] 3.1 Add a short note (system.md and/or runbook local section) that local Compose uses `nginx/local.conf` (HTTP only) and prod uses `nginx/default.conf` + certs — do not change A7 cert generation steps

## 4. Verify

- [x] 4.1 Recreate local nginx (`docker compose up -d --force-recreate nginx` or equivalent) and confirm container status is running, not Restarting
- [x] 4.2 `GET http://127.0.0.1/health` succeeds; optional: `POST http://127.0.0.1/auth/login` returns an application HTTP status (not connection refused)
- [x] 4.3 Sanity-check that prod compose still references `default.conf` + certs (`docker compose -f docker-compose.prod.yml config` or file review) so hosted TLS path is untouched
