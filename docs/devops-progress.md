# DevOps progress (DashNoteSystem)

> **Owns:** learner path, phase order, skills ledger, “what’s next.”  
> **Does not own:** shell commands (use the [runbook](deployment/runbook.md)), 7P engineering steps ([production.md](documentation/production.md)), or hire-gate claims ([goal.md A-gate](documentation/blueprint/goal.md)).  
> **Sync rule:** when A4 or A7 flips, update **this file** and **goal.md** together.

Status glyphs: `✅` done · `⬜` todo · `🚧` in progress · `⛔` blocked (note why)

---

## How to use this doc

1. Read **Current level** — one line on where you are.
2. Work only the **active phase** (do not start Bedrock until Phase 1–3 are honest).
3. For commands, open the [VPS deploy runbook](deployment/runbook.md) — do not copy long command dumps into this file.
4. Check boxes here when you have **proof** (URL, workflow run, smoke exit 0).
5. Revisit weekly; keep Phase 5 extras capped at **≤2** after Bedrock.

**Learning rule:** no abstract AWS study. Each checkbox should leave a URL, screenshot, or green workflow you can point to in an interview.

---

## Current level (one-line status)

**Phase 1 — HTTP first-boot (A4) open.** Platform code/docs (7P.1–7P.8) exist; live `http://<vps-ipv4>/health` + prod smoke not yet proven. No domain → A7 / production-live not claimed. Bedrock deferred.

_Last reviewed: 2026-09-09_

---

## Architecture snapshot (thin VPS + hosted plane)

```
┌─────────────────────────────────────────────────────────┐
│  AWS EC2 t3.small (~2 GB) — thin compute                │
│  nginx :80  →  api :8000 (unpublished)  +  ARQ worker   │
│  migrate oneshot · optional prometheus (off first-boot) │
└───────────────────────────┬─────────────────────────────┘
                            │ .env URLs only
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   Hosted Postgres     Hosted Redis        Qdrant Cloud
        ▼
   Object store (R2 / S3-compatible)
        ▼
   LLM via LiteLLM (NIM / Gemini today → Bedrock in Phase 4)
```

| On VPS | Off VPS (hosted) |
|--------|------------------|
| api, worker, migrate, nginx | Postgres, Redis, Qdrant, R2 |
| GitHub Actions CD pulls GHCR image | Secrets live in VPS `.env` + GH deploy secrets |

Laws: [deploy-low.md](documentation/deploy-low.md) · Compose: [`docker-compose.prod.yml`](../docker-compose.prod.yml) only on the box (never full local compose).

---

## Phase 0 — Platform artifacts (mostly done)

**Why:** Ship path is already designed; you are proving it live, not inventing CI/CD from scratch.

| Item | Status | Proof |
|------|--------|-------|
| 7P.1 Env contract (`.env.example` / `.env.production.example`) | ✅ | [`.env.production.example`](../.env.production.example) |
| 7P.2 `docker-compose.prod.yml` (no db/redis/qdrant) | ✅ | [`docker-compose.prod.yml`](../docker-compose.prod.yml) |
| 7P.3 Soft Qdrant boot | ✅ | API/worker start without hard AI gate |
| 7P.4 R2 / storage contract | ✅ | [storage.md](deployment/storage.md) |
| 7P.5 Deploy scripts + runbook | ✅ | [`scripts/deploy/`](../scripts/deploy/) · [runbook](deployment/runbook.md) |
| 7P.6 `smoke_prod.py` + `/health` / `/health/ai` | ✅ | [`scripts/smoke_prod.py`](../scripts/smoke_prod.py) (local smoke PASS; **prod URL still open**) |
| 7P.7 CI (`pytest` + docker build) | ✅ | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| 7P.8 CD workflow (tag `v*` / `workflow_dispatch`) | ✅ | [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) (**live VPS success still required**) |
| Hosted data plane provisioned (A1) | ✅ | Operator-confirmed; credentials on VPS `.env` only |

**Do next:** leave Phase 0; start Phase 1.

**Skills this phase teaches:** env contracts, thin vs fat compose, soft vs hard health, CI without prod secrets.

---

## Phase 1 — HTTP first-boot (A4)

**Why:** Prove the thin stack on the real EC2 box over HTTP before TLS or Bedrock. Commands: [runbook §2](deployment/runbook.md).

| Item | Status | Proof |
|------|--------|-------|
| EC2 reachable (SSH); Docker + Compose plugin OK | ⬜ | SSH session + `docker compose version` |
| Security group: 22 + 80; **not** 8000 | ⬜ | SG rules reviewed |
| Swap (~2G) if needed on t3.small | ⬜ | `swapon --show` |
| `.env` on VPS from `.env.production.example` | ⬜ | File on box; **not** in git |
| Hosted PG / Redis / Qdrant reachable from VPS | ⬜ | `nc` / curl probes from runbook |
| Image pulled or built; migrate + `up` | ⬜ | Containers healthy |
| `GET http://<vps-ipv4>/health` → 200 | ⬜ | curl / browser |
| `SMOKE_BASE_URL=http://<vps-ipv4>` smoke exit 0 | ⬜ | A4 HTTP proof |
| Sync A4 in [goal.md](documentation/blueprint/goal.md) when green | ⬜ | A-gate row |

**Do next:**

1. Fill gitignored `.env.production` → `scp` to VPS as `.env` ([runbook §2.3](deployment/runbook.md)).
2. Probe hosted plane from the VPS; fix allowlists/SSL before blaming the app.
3. Prefer `IMAGE=ghcr.io/...` pull over building on 2 GB RAM.
4. `migrate` → `up` → health → `python scripts/smoke_prod.py`.
5. Prefer **manual first-boot** before relying on Actions (safer on small instance).

**Skills this phase teaches:** EC2, security groups, SSH, Docker Compose on thin RAM, hosted dependency reachability, health as a gate.

---

## Phase 2 — GitHub CD proof

**Why:** Same deploy path, but Actions builds/pushes GHCR and SSHs the box. Workflow already exists — you need one green live run. Commands: [runbook CD section](deployment/runbook.md); workflow: [`deploy.yml`](../.github/workflows/deploy.yml).

| Item | Status | Proof |
|------|--------|-------|
| Repo secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `SMOKE_BASE_URL` | ⬜ | GitHub → Settings → Secrets |
| Optional: `SMOKE_EMAIL` / `SMOKE_PASSWORD`, `GHCR_TOKEN` | ⬜ | If private package / auth smoke |
| Optional var: `VPS_APP_DIR` (default `/opt/dashnote`) | ⬜ | Matches real app dir on box |
| `workflow_dispatch` **or** tag `v*` succeeds | ⬜ | Actions run green |
| Post-deploy health + smoke from Actions | ⬜ | Job log + smoke step |
| Know how to roll back (redeploy previous image tag) | ⬜ | Tag noted |

**Do next:**

1. Wire secrets after Phase 1 manual boot works (or in parallel if `.env` already solid).
2. Run `workflow_dispatch` once; fix SSH/path/login before tagging releases.
3. Keep **no auto-deploy on every `main` push** until you are bored of being safe.

**Skills this phase teaches:** GHCR, deploy secrets vs app `.env`, SSH CD, migrate-before-roll, smoke as CD hard gate, rollback by image tag.

---

## Phase 3 — HTTPS / production-live (A7)

**Why:** HTTP-on-IP is first-boot only. Hire/production-live needs TLS + domain. See runbook TLS notes / 7P.5.

| Item | Status | Proof |
|------|--------|-------|
| Domain + DNS → VPS | ⬜ | `api.<domain>` resolves |
| TLS (Caddy / Certbot / Cloudflare) | ⬜ | Cert valid |
| SG / edge: **443** open; still no public **8000** | ⬜ | SG rules |
| `CORS_ORIGINS` includes real frontend origin (not `*`) | ⬜ | VPS `.env` |
| `GET https://api.<domain>/health` → 200 | ⬜ | curl |
| HTTPS `smoke_prod.py` exit 0 | ⬜ | A4 HTTPS + A7 |
| Sync A7 in [goal.md](documentation/blueprint/goal.md) | ⬜ | A-gate row |

**Do next:** pick domain + TLS path only after Phase 1 (and ideally Phase 2) are green. Do not block Bedrock learning on perfect CDN setup if HTTPS smoke already passes.

**Skills this phase teaches:** DNS, TLS termination, CORS for real origins, “production-live” vs first-boot claims.

---

## Phase 4 — Bedrock by doing

**Deferred until Phase 1–3 are honest.** Do not rewrite the agent onto “Bedrock Agents.” Keep LangGraph; swap the **model provider** via LiteLLM.

| Item | Status | Proof |
|------|--------|-------|
| IAM principal can invoke Bedrock in one region | ⬜ | IAM policy / console |
| Model access enabled (chat; embed optional) | ⬜ | Bedrock model access |
| `LLM_MODEL` (and/or fallbacks) → Bedrock LiteLLM id | ⬜ | VPS `.env` / settings |
| Prod chat or agent call succeeds | ⬜ | HTTP 200 + useful reply |
| Trace visible in Langfuse (if configured) | ⬜ | Trace link |
| Fallback story if Bedrock throttles | ⬜ | Fallback model still works |

**Do next (when unlocked):** one region, one chat model, prove `/ai/chat` or `/ai/agent`, document cost/region in a sentence for interviews.

**Skills this phase teaches:** IAM for models, Bedrock access, provider-agnostic LiteLLM, cost/throttle awareness — **without** boiling the product.

---

## Phase 5 — Optional extras (cap ≤2)

**Only after Phase 4 feels boring.** Pick at most two. Skip anything that does not leave new proof.

| Extra | Status | Worth it if… | Skip if… |
|-------|--------|--------------|----------|
| S3 instead of R2 | ⬜ | Want pure-AWS storage talk | R2 already works |
| OIDC → ECR (no long-lived pull token) | ⬜ | Want modern CD bullet | CD already reliable |
| RDS instead of current Postgres host | ⬜ | Want managed DB story | Hosted PG is fine |
| ECS/Fargate | ⬜ | Want orchestration bullet | Compose ops not calm yet |
| Terraform / IaC | ⬜ | Want IaC bullet | Still fighting first deploy |

**Skills this phase teaches:** deliberate AWS swaps, saying “no” to resume padding.

---

## Skills ledger (resume bullets)

Fill as phases close. Prefer proof over buzzwords.

| Phase | Skill / bullet seed | Proof when ✅ |
|-------|---------------------|---------------|
| 0 | Designed thin VPS + hosted data plane; CI without prod secrets | workflows + compose in repo |
| 1 | Deployed FastAPI + ARQ worker on AWS EC2; SG + health gates | `http://…/health` + smoke |
| 2 | CD: GHCR build/push → SSH migrate/roll → smoke hard gate | green Actions run |
| 3 | TLS production API; CORS locked to real FE origin | `https://…/health` + smoke |
| 4 | LiteLLM → Bedrock in prod; RAG/agent unchanged | live AI call + optional Langfuse |
| 5 | _(optional)_ S3 / ECR OIDC / RDS / ECS — only if done | matching resource + deploy proof |

**Target resume line (after Phase 1–4):**  
*Shipped multi-tenant RAG/agent API on AWS EC2 with Docker CI/CD (migrate → roll → smoke), workers + vector search, LiteLLM with Bedrock in production, Langfuse tracing.*

---

## Sources of truth (links)

| Topic | Link |
|-------|------|
| Progress / learner path | **This file** |
| Deploy commands | [deployment/runbook.md](deployment/runbook.md) |
| Storage (R2) | [deployment/storage.md](deployment/storage.md) |
| 7P engineering checklist | [documentation/production.md](documentation/production.md) |
| Hire / A-gate | [documentation/blueprint/goal.md](documentation/blueprint/goal.md) |
| Platform laws | [documentation/deploy-low.md](documentation/deploy-low.md) |
| Prod env template | [`.env.production.example`](../.env.production.example) |
| Prod compose | [`docker-compose.prod.yml`](../docker-compose.prod.yml) |
| CI | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| CD | [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) |
| Smoke | [`scripts/smoke_prod.py`](../scripts/smoke_prod.py) |
| Deploy scripts | [`scripts/deploy/`](../scripts/deploy/) |
