# Edge: aisystem.world (API)

> **Owns:** how `api.aisystem.world` reaches the thin VPS and who owns each layer.  
> **Does not own:** deploy shell steps ([runbook](runbook.md)), Terraform import stages ([terraform-a.md](terraform-a.md)), or frontend hosting.

## Hostnames

| Hostname | Target | Role |
|----------|--------|------|
| `api.aisystem.world` | EC2 public IP (today `16.192.166.178`) via Cloudflare | Production API |
| `aisystem.world` (apex) | **Not this VPS** — future frontend host | Browser UI origin for CORS |

VPS runs **api + worker + nginx only**. Hosted Postgres / Redis / Qdrant / R2 stay off-box. Do **not** run the sibling frontend on this EC2.

## Ownership map

```
Browser
   │  HTTPS
   ▼
Cloudflare (DNS + browser TLS; Flexible → origin HTTP :80)
   │  HTTP :80
   ▼
AWS EC2 + security group (Terraform Level A)
   │  Docker network
   ▼
nginx → api :8000 (unpublished) + ARQ worker
   │
   └── .env URLs → hosted data plane
```

| Layer | Owner | Notes |
|-------|--------|------|
| DNS `api` A record, orange-cloud proxy, SSL mode | Cloudflare | Not managed by Terraform in Level A |
| EC2 instance, SG (22/80/443; never public 8000) | Terraform (`infra/`) | SSH by **public IP**, never via proxied hostname |
| api, worker, nginx, `.env` | Docker Compose + operator / CD | `docker-compose.prod.yml` only |

## Current TLS choice (A7)

- **Cloudflare SSL/TLS mode: Flexible** — HTTPS to clients; Cloudflare speaks HTTP to nginx `:80`.
- Origin does **not** need a VPS certificate for this path.
- Upgrade path later: Full / Full (strict) + Caddy or Certbot on the box (see runbook TLS options).

## Operator checklist (API hostname)

1. Cloudflare DNS: A `api` → VPS IPv4, **Proxied**.
2. SSL/TLS → **Flexible**.
3. `curl -sS https://api.aisystem.world/health`
4. VPS `.env`: `CORS_ORIGINS` includes `https://aisystem.world`, never `*`.
5. Restart api; HTTPS smoke: `SMOKE_BASE_URL=https://api.aisystem.world python scripts/smoke_prod.py`
6. CD: set GitHub `SMOKE_BASE_URL` to that HTTPS URL; keep `VPS_HOST` as the SSH IP.

## Follow-ons (not this edge)

- Apex frontend hosting + `NEXT_PUBLIC_API_BASE_URL=https://api.aisystem.world`
- Cloudflare Full + origin cert
- Bedrock
