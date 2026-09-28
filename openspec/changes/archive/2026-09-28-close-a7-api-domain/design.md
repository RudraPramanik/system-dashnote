## Context

See `proposal.md` for why. The thin VPS already serves api/worker/nginx on HTTP `:80` (`docker-compose.prod.yml`). Terraform manages EC2 + SG (Level A done). Hosted Postgres/Redis/Qdrant/R2 stay off-box. Cloudflare now protects `aisystem.world`. Frontend will be `https://aisystem.world` on a **non-VPS** host later — never on this EC2. This change closes A7 for the API hostname only.

## Goals / Non-Goals

**Goals:**

- `api.aisystem.world` resolves and `https://api.aisystem.world/health` + HTTPS smoke pass (A7).
- VPS `.env` CORS lists `https://aisystem.world` (prep for FE).
- Document Cloudflare vs nginx vs Terraform ownership.
- Point CD smoke at the HTTPS API URL; allow one green deploy attempt.

**Non-Goals:**

- Hosting or deploying the frontend (any provider).
- Putting FE on the VPS or Vercel as part of this change.
- Origin certificates / Cloudflare Full (strict) — optional later (self-signed for Full non-strict is in scope when Flexible returns 521).
- Terraform-managed DNS (Route53/Cloudflare provider).
- Bedrock / LLM provider changes.
- Rewriting `deploy.yml` triggers or compose topology.

## Decisions

### D1 — Cloudflare Full + origin self-signed for A7

Browser TLS terminates at Cloudflare. Origin nginx publishes `:80` and `:443` with a **self-signed** cert under `nginx/certs/` (gitignored). SSL mode **Full** (not Full strict).

**Why:** Zone returned Cloudflare **521** while origin was HTTP-only (Full without `:443`). Self-signed unblocks Full without Let’s Encrypt on a 2 GB box.

**Alternatives:** Flexible with origin HTTP-only (works only if SSL mode is Flexible). Full strict + Cloudflare origin CA / LE (deferred).

### D2 — DNS: A record `api` → current public IP

Content: `16.192.166.178` (or EIP if associated later). Proxied (orange). Apex `@` for FE is **out of scope** here except documenting the intended CORS origin.

### D3 — CORS before FE ships

Set `CORS_ORIGINS=["https://aisystem.world"]` on the VPS (MAY also keep localhost entries for local FE against prod API). Never `*`. Restart api after change.

### D4 — Documentation surface

| Doc | Role |
|-----|------|
| `docs/deployment/runbook.md` | Commands: DNS checklist, Full SSL + origin cert, CORS, HTTPS smoke, CD secret values |
| `docs/deployment/edge-aisystem.md` (new) or runbook § | Ownership diagram: Cloudflare / EC2+SG (TF) / Compose |
| `docs/devops-progress.md` | Phase 3 A7 → ✅ when proven; Phase 2 CD status |
| `goal.md` | A7 row flips with proof URL |

### D5 — CD in this change

Update operator secrets: `SMOKE_BASE_URL=https://api.aisystem.world`; `VPS_HOST` may stay IP (SSH) or hostname if DNS works for SSH (prefer IP for SSH). One `workflow_dispatch` attempt is in scope as proof; FE still not required.

## Risks / Trade-offs

- **[Risk] Full with self-signed is not Full strict** → Mitigation: document; upgrade to origin CA / LE later; never claim strict.
- **[Risk] Cloudflare orange cloud breaks SSH if someone points SSH at the proxied hostname** → Mitigation: SSH only to raw IP; document that.
- **[Risk] CORS set before FE exists** → Mitigation: harmless; FE change will use that origin.
- **[Risk] CD fails on path/login** → Mitigation: Phase 2 checklist; fix without blocking A7 if HTTPS smoke already passed manually.
- **[Risk] CD wipe of VPS-only nginx TLS** → Mitigation: commit compose `443` publish + nginx SSL server; keep certs gitignored on box.

## Migration Plan

1. Cloudflare DNS: A `api` → VPS IP, proxied.
2. Ensure SSL Full + origin `:443` (or Flexible if deliberately HTTP-only).
3. Wait for resolution; curl HTTPS health.
4. Update VPS `.env` CORS; restart api/worker as needed.
5. HTTPS smoke; flip A7 in progress + goal.md.
6. Document edge ownership.
7. Set GH secrets; optional `workflow_dispatch`.
8. Rollback DNS: remove/disable `api` record or grey-cloud; CORS revert; A7 claims stay false.

## Open Questions

- None blocking. Exact FE host provider for apex is deferred to the frontend change.
