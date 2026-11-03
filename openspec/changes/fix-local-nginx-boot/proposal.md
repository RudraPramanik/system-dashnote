## Why

Local `docker compose up` leaves nginx crash-looping because the shared `nginx/default.conf` requires TLS certs (`origin.crt` / `origin.key`) that exist only on the hosted VPS. Developers then see `POST http://127.0.0.1/auth/login` → `net::ERR_CONNECTION_REFUSED` even when the API container is up. Hosted `api.aisystem.world` must stay on Cloudflare Full + origin `:443` unchanged.

## What Changes

- Split local vs production nginx config so local Compose boots HTTP `:80` without any TLS files.
- Point `docker-compose.yml` (local full stack) at the HTTP-only config.
- Keep `docker-compose.prod.yml` and the production nginx SSL server block / cert mount as they are today (no hosted behavior change).
- Document the local vs prod nginx files briefly where operators already look for Compose edge setup.
- **Non-goals:** frontend env changes, AWS/Cloudflare/DNS changes, generating committed certs, fixing unrelated host `:8000` bind conflicts.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Strengthen the local-compose edge requirement so nginx on the developer path MUST start and serve hard health on `http://127.0.0.1` without TLS certificates, while production compose MUST continue to require origin TLS for `:443`.

## Impact

- `nginx/` config files (add local HTTP-only config; leave prod SSL config path used by prod compose intact)
- `docker-compose.yml` nginx volume mount
- Light doc touch (runbook / system / frontendguide as needed) — not VPS deploy scripts
- No API, auth, DB, or frontend code changes
- Hosted stack (`docker-compose.prod.yml`, VPS certs, Cloudflare Full) unchanged by design
