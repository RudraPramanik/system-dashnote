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
- Origin certificates / Cloudflare Full (strict) — optional later.
- Terraform-managed DNS (Route53/Cloudflare provider).
- Bedrock / LLM provider changes.
- Rewriting `deploy.yml` triggers or compose topology.

## Decisions

### D1 — Cloudflare Flexible for A7 now

Browser TLS terminates at Cloudflare; origin remains nginx HTTP `:80`. SSL mode **Flexible**.

**Why:** Matches current compose (443 commented). Fastest path to a public HTTPS API URL.

**Alternatives:** Full + Caddy/Certbot on VPS (better crypto to origin; more work on 2 GB). DNS-only + LE on box (no CF proxy). Deferred.

### D2 — DNS: A record `api` → current public IP

Content: `16.192.166.178` (or EIP if associated later). Proxied (orange). Apex `@` for FE is **out of scope** here except documenting the intended CORS origin.

### D3 — CORS before FE ships

Set `CORS_ORIGINS=["https://aisystem.world"]` on the VPS (MAY also keep localhost entries for local FE against prod API). Never `*`. Restart api after change.

### D4 — Documentation surface

| Doc | Role |
|-----|------|
| `docs/deployment/runbook.md` | Commands: DNS checklist, Flexible SSL, CORS, HTTPS smoke, CD secret values |
| `docs/deployment/edge-aisystem.md` (new) or runbook § | Ownership diagram: Cloudflare / EC2+SG (TF) / Compose |
| `docs/devops-progress.md` | Phase 3 A7 → ✅ when proven; Phase 2 CD status |
| `goal.md` | A7 row flips with proof URL |

### D5 — CD in this change

Update operator secrets: `SMOKE_BASE_URL=https://api.aisystem.world`; `VPS_HOST` may stay IP (SSH) or hostname if DNS works for SSH (prefer IP for SSH). One `workflow_dispatch` attempt is in scope as proof; FE still not required.

## Risks / Trade-offs

- **[Risk] Flexible is not end-to-end encryption** → Mitigation: document as interim; upgrade to Full later; never claim Full.
- **[Risk] Cloudflare orange cloud breaks SSH if someone points SSH at the proxied hostname** → Mitigation: SSH only to raw IP; document that.
- **[Risk] CORS set before FE exists** → Mitigation: harmless; FE change will use that origin.
- **[Risk] CD fails on path/login** → Mitigation: Phase 2 checklist; fix without blocking A7 if HTTPS smoke already passed manually.
- **[Risk] Wrong SSL mode (Full without origin cert)** → Mitigation: runbook says Flexible until origin cert exists.

## Migration Plan

1. Cloudflare DNS: A `api` → VPS IP, proxied; SSL Flexible.
2. Wait for resolution; curl HTTPS health.
3. Update VPS `.env` CORS; restart api/worker as needed.
4. HTTPS smoke; flip A7 in progress + goal.md.
5. Document edge ownership.
6. Set GH secrets; optional `workflow_dispatch`.
7. Rollback DNS: remove/disable `api` record or grey-cloud; CORS revert; A7 claims stay false.

## Open Questions

- None blocking. Exact FE host provider for apex is deferred to the frontend change.
