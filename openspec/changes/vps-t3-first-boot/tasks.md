## 1. Env contract (no secrets in git)

- [ ] 1.1 Confirm `.gitignore` still ignores `.env.*` except `.env.example` and `.env.production.example`
- [ ] 1.2 Update `.env.production.example` comments for HTTP first-boot: copy to gitignored `.env.production` then VPS `.env`; `CORS_ORIGINS` MUST NOT be `*`; `STORAGE_BACKEND=r2`; `REDIS_URL` / `ARQ_REDIS_URL` MAY be the same host
- [ ] 1.3 Do not add a committed filled `.env.production`; do not change FastAPI settings names unless a comment-only mismatch is found

## 2. Runbook — thin VPS first-boot

- [ ] 2.1 Add a first-boot section to `docs/deployment/runbook.md`: SSH, Docker + Compose plugin, security group/ufw (22 + 80, api `:8000` unpublished), hosted-plane connectivity check from the VPS
- [ ] 2.2 Document 2 GB RAM rules: `docker-compose.prod.yml` only; never local `docker-compose.yml` on the VPS; Prometheus profile off; frontend off-box; 1–2 GiB swap recommended
- [ ] 2.3 Document image strategy: prefer `IMAGE=` pull; fallback swap + on-box build
- [ ] 2.4 Document HTTP-on-IP proof: `curl http://<vps-ipv4>/health` then `SMOKE_BASE_URL=http://<vps-ipv4> python scripts/smoke_prod.py`; fallback on-VPS smoke against `http://127.0.0.1` plus external curl
- [ ] 2.5 State explicitly that HTTP-IP PASS is first-boot only — not A7, not production-live, not hire-ready; TLS remains a later decision

## 3. Topology and ship-path trackers

- [ ] 3.1 Update `docs/documentation/production.md` topology from Oracle ~8 GB to AWS t3.small ~2 GB / 30 GiB thin compute + hosted data plane
- [ ] 3.2 Update `docs/documentation/blueprint8.md` active window: local Tier 1 complete; VPS work resumed as HTTP first-boot; HTTPS A4/A7 still required before production-live
- [ ] 3.3 Update `docs/documentation/blueprint/goal.md`: mark A1 complete (operator-confirmed); leave A7/B7/job-search open; A4 note HTTP-IP first-boot vs HTTPS
- [ ] 3.4 Align `docs/ship-plan.md` deferred-window text so it does not contradict resumed VPS first-boot
- [ ] 3.5 Confirm root README does not present an HTTP IP as a stranger TLS demo or production-live URL

## 4. Operator first-boot (evidence)

- [ ] 4.1 Fill local gitignored `.env.production` from the example (hosted URLs, R2, JWT, LLM keys); copy to VPS as `.env`
- [ ] 4.2 On the t3.small: Docker + Compose, swap if needed, SG/ufw, repo files present
- [ ] 4.3 Run `scripts/deploy/migrate.sh`, `up.sh`, `health-check.sh` with observability profile **off**
- [ ] 4.4 Record `GET http://<vps-ipv4>/health` success for hard deps (Postgres + Redis)
- [ ] 4.5 Record `scripts/smoke_prod.py` exit 0 against that HTTP base URL (hard gate only; `--with-ai` optional/soft)
- [ ] 4.6 Write the HTTP-IP PASS note into `goal.md` A4 without checking A7 or production-live

## 5. Alive / honesty checks

- [ ] 5.1 Confirm local `docker compose up` path is unchanged (no prod-only overrides leaked into `docker-compose.yml`)
- [ ] 5.2 Confirm `/ai/chat*` and `/ai/agent*` both remain; no GraphRAG/multi-agent/HITL scope in this change
- [ ] 5.3 Confirm no production secrets, VPS keys, or filled env files were committed
- [ ] 5.4 Confirm GitHub CD HTTPS success was **not** required to close this change
