## Context

Slice 8X deploy-first order places **7P.5 (deploy scripts + runbook)** after storage contract (7P.4) and thin CI (7P.7). `docker-compose.prod.yml` already defines `migrate`, `api`, `worker`, `nginx`, and optional `prometheus` (observability profile). Hosted Postgres/Redis/Qdrant/R2 URLs come from VPS `.env`. No `scripts/deploy/` helpers or `docs/deployment/runbook.md` exist yet — operators cannot follow a repeatable manual release sequence before smoke (7P.6) and CD (7P.8).

## Goals / Non-Goals

**Goals:**

- Publish an operator runbook for first-time VPS setup and every-release deploy
- Add bash helpers: migrate → up (api healthy, then worker + nginx) → health-check against hard `/health`
- Document TLS options as a decision (Cloudflare / Caddy / Certbot) without implementing cert install in this change
- Keep secrets out of scripts; validate prod compose config still parses
- Mark `production.md` 7P.5 done

**Non-Goals:**

- Real VPS provisioning or DNS changes
- Implementing TLS termination or replacing nginx
- `scripts/smoke_prod.py` / `GET /health/ai` (7P.6)
- GitHub CD / SSH deploy (7P.8)
- Changing local `docker-compose.yml` or app runtime code
- Claiming “production live” (blocked until 7P.8 smoke)

## Decisions

1. **Bash scripts for VPS; PowerShell only as runbook notes**  
   Rationale: Target host is Linux; Windows local operators still use `docker compose` manually.  
   Alternative: Dual PowerShell + bash — rejected; increases drift for one-time manual path.

2. **Hard-code `-f docker-compose.prod.yml` in helpers**  
   Rationale: Blueprint law; prevents accidental use of local full-stack compose on the VPS.  
   Alternative: `COMPOSE_FILE` env override — optional later; not required for 7P.5.

3. **`up.sh` starts api first, waits for health, then worker + nginx**  
   Rationale: Matches prod compose `worker depends_on api: service_healthy` and avoids racing nginx against a cold API.  
   Alternative: Single `up -d` for all services — acceptable but weaker feedback; prefer sequenced up for manual ops.

4. **`health-check.sh` hits `http://127.0.0.1/health` (nginx edge)**  
   Rationale: Prod edge is nginx on port 80; hard health is db+redis only (Qdrant soft). Prefer `curl -sf` + optional `jq`; if `jq` missing, accept curl exit + grep for ok/status.  
   Alternative: Hit `api:8000` from host — fails without publish; stay on published 80.

5. **TLS is decision documentation only**  
   Rationale: Blueprint defers cert wiring; runbook lists Cloudflare / Caddy / Certbot so 7P.8 operators can pick one.  
   Alternative: Ship Certbot compose now — rejected; out of 7P.5 scope.

6. **LF line endings + document `chmod +x`**  
   Rationale: Windows checkout can break shebangs with CRLF; runbook must call this out.  
   Alternative: gitattributes for `scripts/deploy/*.sh` — recommended in tasks if easy; not a blocker.

## Risks / Trade-offs

- **[Risk] Scripts never executed on real VPS in this change** → Mitigation: Validate `docker compose -f docker-compose.prod.yml config`; full VPS proof is 7P.8 gate.  
- **[Risk] `jq` absent on minimal VPS** → Mitigation: health-check falls back to curl success + status string check.  
- **[Risk] Operator runs local compose on VPS** → Mitigation: Scripts hard-code prod file; runbook warns.  
- **[Risk] Secrets pasted into scripts** → Mitigation: Explicit law: env_file `.env` only; never commit filled `.env`.  
- **Trade-off:** Manual deploy path exists before CD — intentional; CD will wrap the same sequence later.

## Migration Plan

1. Add `docs/deployment/runbook.md` and `scripts/deploy/{migrate,up,health-check}.sh`.  
2. Optionally set `.gitattributes` for `*.sh text eol=lf`.  
3. Mark tracker 7P.5 done.  
4. Rollback: delete scripts/runbook and revert tracker; no DB or app rollback.

## Open Questions

- None blocking apply. Preferred TLS option can stay “operator picks one” until a concrete VPS is provisioned for 7P.8.
