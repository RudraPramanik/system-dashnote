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
Cloudflare (DNS + browser TLS; Full → origin HTTPS :443)
   │  HTTPS :443 (self-signed origin cert OK for Full, not Full strict)
   ▼
AWS EC2 + security group (Terraform Level A)
   │  Docker network
   ▼
nginx → api :8000 (unpublished) + ARQ worker
   │
   └── .env URLs → hosted data plane
```

| Layer | Owner | Notes |
|--------|------|------|
| DNS `api` A record, orange-cloud proxy, SSL mode | Cloudflare | Not managed by Terraform in Level A |
| EC2 instance, SG (22/80/443; never public 8000) | Terraform (`infra/`) | SSH by **public IP**, never via proxied hostname |
| api, worker, nginx, `.env`, origin cert under `nginx/certs/` | Docker Compose + operator / CD | `docker-compose.prod.yml` only |

## Current TLS choice (A7)

- **Cloudflare SSL/TLS mode: Full** (zone default; Flexible alone returned **521** while origin had no `:443`).
- Origin nginx publishes **`:80` and `:443`**. Self-signed cert at `nginx/certs/origin.{crt,key}` (gitignored) is enough for **Full**, not **Full (strict)**.
- Browser TLS is still Cloudflare’s certificate; clients never see the origin self-signed cert.
- Upgrade path later: Full (strict) + Cloudflare origin cert or Let’s Encrypt (see runbook).

## Operator checklist (API hostname)

1. Cloudflare DNS: A `api` → VPS IPv4, **Proxied**.
2. SSL/TLS → **Full** (with origin `:443`) — or **Flexible** if you deliberately keep origin HTTP-only.
3. On VPS: generate origin cert if missing (runbook §5), ensure compose publishes `443:443`.
4. `curl -sS https://api.aisystem.world/health`
5. VPS `.env`: `CORS_ORIGINS` includes `https://aisystem.world`, never `*`.
6. Restart api; HTTPS smoke: `SMOKE_BASE_URL=https://api.aisystem.world python scripts/smoke_prod.py`
7. CD: set GitHub `SMOKE_BASE_URL` to that HTTPS URL; keep `VPS_HOST` as the SSH IP.
8. Agent HITL: `curl -sS https://api.aisystem.world/health/ai` must show `dependencies.checkpointer.reachable: true` before treating hosted agent create-note as healthy (see runbook §7 checkpointer diagnosis). Soft: `python scripts/smoke_prod.py --with-ai`.

## Proof (2026-09-28)

- `GET https://api.aisystem.world/health` → 200
- `SMOKE_BASE_URL=https://api.aisystem.world python scripts/smoke_prod.py` → exit 0 (HARD GATE PASS)

## Follow-ons (not this edge)

- Apex frontend hosting + `NEXT_PUBLIC_API_BASE_URL=https://api.aisystem.world`
- Cloudflare Full (strict) + origin / Let’s Encrypt cert
- Bedrock
