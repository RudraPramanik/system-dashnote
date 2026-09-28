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

**Phase 2–3 ✅.** A7 live at `https://api.aisystem.world`; CD green via `workflow_dispatch` ([run 36405607524](https://github.com/RudraPramanik/system-dashnote/actions/runs/36405607524), 2026-09-28). **Next:** apex FE host (not this VPS), then Bedrock. See [`deployment/edge-aisystem.md`](deployment/edge-aisystem.md).

_Last reviewed: 2026-09-28_

---

## Architecture snapshot (thin VPS + hosted plane)

```
┌─────────────────────────────────────────────────────────┐
│  AWS EC2 t3.small (~2 GB) — thin compute                │
│  nginx :80/:443  →  api :8000 (unpublished)  +  ARQ worker   │
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
| 7P.6 `smoke_prod.py` + `/health` / `/health/ai` | ✅ | [`scripts/smoke_prod.py`](../scripts/smoke_prod.py) (local + HTTP-IP 2026-09-12 + **HTTPS A7 PASS 2026-09-28**) |
| 7P.7 CI (`pytest` + docker build) | ✅ | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| 7P.8 CD workflow (tag `v*` / `workflow_dispatch`) | ✅ | [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) (**live VPS success still required**) |
| Hosted data plane provisioned (A1) | ✅ | Operator-confirmed; credentials on VPS `.env` only |

**Do next:** Phase 0–3 are proven (HTTP first-boot, HTTPS A7, CD). Prefer apex FE next; Bedrock after.

**Skills this phase teaches:** env contracts, thin vs fat compose, soft vs hard health, CI without prod secrets.

---

## Phase 1 — HTTP first-boot (A4)

**Why:** Prove the thin stack on the real EC2 box over HTTP before TLS or Bedrock. Commands: [runbook §2](deployment/runbook.md).

| Item | Status | Proof |
|------|--------|-------|
| EC2 reachable (SSH); Docker + Compose plugin OK | ✅ | First-boot window 2026-09-12 |
| Security group: 22 + 80; **not** 8000 | ✅ | HTTP :80 health reachable; api unpublished |
| Swap (~2G) if needed on t3.small | ✅ | Operator first-boot (t3.small) |
| `.env` on VPS from `.env.production.example` | ✅ | File on box; **not** in git |
| Hosted PG / Redis / Qdrant reachable from VPS | ✅ | Health + smoke against hosted plane |
| Image pulled or built; migrate + `up` | ✅ | Containers healthy; smoke exit 0 |
| `GET http://<vps-ipv4>/health` → 200 | ✅ | HTTP-IP first-boot 2026-09-12 |
| `SMOKE_BASE_URL=http://<vps-ipv4>` smoke exit 0 | ✅ | A4 HTTP proof (goal.md) |
| Sync A4 in [goal.md](documentation/blueprint/goal.md) when green | ✅ | A4 ✅ PASS 2026-09-12 |

**Do next:**

1. Prefer apex FE hosting (CORS already lists `https://aisystem.world`).
2. Prefer `IMAGE=ghcr.io/...` pull over building on 2 GB RAM for later rolls.

**Skills this phase teaches:** EC2, security groups, SSH, Docker Compose on thin RAM, hosted dependency reachability, health as a gate.

---

## Phase 2 — GitHub CD proof

**Why:** Same deploy path, but Actions builds/pushes GHCR and SSHs the box. Workflow already exists — you need one green live run. Commands: [runbook CD section](deployment/runbook.md); workflow: [`deploy.yml`](../.github/workflows/deploy.yml).

| Item | Status | Proof |
|------|--------|-------|
| Repo secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `SMOKE_BASE_URL` | ✅ | Set 2026-09-28; smoke URL `https://api.aisystem.world` |
| Optional: `SMOKE_EMAIL` / `SMOKE_PASSWORD`, `GHCR_TOKEN` | ⬜ | Not required for first green run (public GHCR pull path) |
| Optional var: `VPS_APP_DIR` (default `/opt/dashnote`) | ✅ | `/opt/dashnote` |
| `workflow_dispatch` **or** tag `v*` succeeds | ✅ | [run 36405607524](https://github.com/RudraPramanik/system-dashnote/actions/runs/36405607524) green |
| Post-deploy health + smoke from Actions | ✅ | SSH health-check + smoke hard gate PASS |
| Know how to roll back (redeploy previous image tag) | ⬜ | Pin prior `IMAGE` tag / re-dispatch |

**Do next:**

1. Prefer tagging releases (`v*`) once you trust dispatch; keep **no auto-deploy on every merge**.
2. Apex FE hosting (CORS already ready) — then Bedrock.

**Skills this phase teaches:** GHCR, deploy secrets vs app `.env`, SSH CD, migrate-before-roll, smoke as CD hard gate, rollback by image tag.

---

## Phase 3 — HTTPS / production-live (A7)

**Why:** HTTP-on-IP first-boot is proven. Production-live needs `https://api.aisystem.world`. Guide: [`deployment/edge-aisystem.md`](deployment/edge-aisystem.md) · commands: [runbook §5](deployment/runbook.md).

| Item | Status | Proof |
|------|--------|-------|
| Cloudflare zone for `aisystem.world` | ✅ | Operator: domain protected by Cloudflare |
| DNS A `api` → VPS IP (proxied) | ✅ | `api` → `16.192.166.178` Proxied |
| SSL mode Full + origin `:443` | ✅ | Self-signed under `nginx/certs/` (Full; not Full strict) |
| SG: 80 (and 443 if needed); **not** public 8000 | ✅ | Terraform-managed SG |
| `CORS_ORIGINS` includes `https://aisystem.world` (not `*`) | ✅ | VPS `.env` + api recreate; contract in `.env.production.example` |
| `GET https://api.aisystem.world/health` → 200 | ✅ | 2026-09-28 |
| HTTPS `smoke_prod.py` exit 0 | ✅ | HARD GATE PASS 2026-09-28 |
| Sync A7 in [goal.md](documentation/blueprint/goal.md) | ✅ | Flipped with HTTPS smoke |

**Do next:** Apex FE hosting is the follow-on (not this VPS). Bedrock stays deferred until FE path is honest.

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
| Terraform / IaC | ✅ | Level A live: EC2 + SG imported, remote state, health + smoke PASS. Blueprint: [`deployment/terraform-a.md`](deployment/terraform-a.md). Level B and Level C not started. | ECS, RDS, and OIDC stay unchecked |

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
| API edge (`api.aisystem.world`) | [deployment/edge-aisystem.md](deployment/edge-aisystem.md) |
| Terraform Level A | [deployment/terraform-a.md](deployment/terraform-a.md) |
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
