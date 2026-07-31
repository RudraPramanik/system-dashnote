## Context

DashNoteSystem is a **multi-tenant notes backend** (no frontend in this repo): FastAPI API + ARQ worker, PostgreSQL, Redis, Qdrant, LiteLLM, LangGraph, Langfuse/Prometheus.

### What we want to achieve

Per `docs/documentation/blueprint/goal.md` and `docs/ship-plan.md`:

1. **Product:** Own orchestration, memory, retrieval, workflows, automation, and tenancy — not LLM inference infra (hosted providers only).
2. **Near-term gate (job search):** Live TLS API, smoke+CI/CD, golden evals (≥80% pass), portfolio packaging (README + demo evidence). Frontend lives outside this repo but is required for the full stranger-test demo.
3. **Later (explicitly deferred):** GraphRAG, multi-agent, hybrid/reranker, automation approval UI, usage metering API, scale caches.

### What is already built (do not rebuild)

| Area | Status | Evidence |
|------|--------|----------|
| Auth / workspaces / membership / notebooks / notes / pages / files | ✅ | `src/*` routers, Alembic, Compose |
| Embed pipeline (chunk → cache → LiteLLM → worker) | ✅ Slice 1 | `ai/embeddings`, `worker/ingestion` |
| RBAC vector search + Qdrant (`notes_chunks`, `files_chunks`, dim 3072) | ✅ Slice 2 | `GET /ai/test-search`, `build_rbac_filter` |
| RAG chat JSON + SSE + citations | ✅ Slices 3–4 | `POST /ai/chat`, `/ai/chat/stream` |
| Threads + conversation memory | ✅ Slice 5 | `GET /ai/threads*` |
| LangGraph agent + note tools | ✅ Slice 6 | `POST /ai/agent*`, `scripts/e2e_agent_test.py` |
| File automation + tagging + governance | ✅ Slice 7 | `emit_event`, `AutomationDecisionEngine` |
| Shared LLM retry / structured layer | ✅ Slice 7.5 | `shared/llm/` |
| Soft Qdrant boot; env contract; prod compose skeleton | ✅ 7P.0–7P.3 | `production.md`, `docker-compose.prod.yml` |
| Local full stack | ✅ | `docker compose up` → `/health` |

### Gaps this change closes

| Gap | Tracker |
|-----|---------|
| R2 storage contract for prod (no shared volume) | 7P.4 |
| Deploy scripts + runbook | 7P.5 |
| `smoke_prod.py` (+ optional `/health/ai`) | 7P.6 |
| CI / CD workflows | 7P.7–7P.8 |
| Golden eval harness | ship-plan Day 12 / goal §C |
| Hireable README packaging | goal §D |

Process ownership: **API** for health/smoke routes; **scripts + GitHub Actions** for deploy/CI; **evals CLI** as a separate process that calls the API (or mocked retrieval) — never invent parallel Qdrant clients in evals.

## Goals / Non-Goals

**Goals:**

- Finish remaining **7P.4–7P.8** platform behaviors without breaking local Compose.
- Ship **`evals/`** with ≥10 golden cases including tenant isolation and a pass/fail CLI.
- Upgrade **root README** (and minimal supporting docs) to portfolio baseline quality.
- Keep architecture laws intact (tenancy, wrappers, soft vs hard deps, chat/agent coexistence).

**Non-Goals:**

- Building or shipping the frontend (B1–B7) inside this repo.
- New AI product slices (7A, 7R, 8, 9, 10 metering, 11).
- Bulk-backfilling OpenSpec specs for every existing domain (auth, notes, …).
- Replacing `/ai/chat*` with the agent or vice versa.
- Hard-failing boot when Qdrant/LLM are down.

## Decisions

### D1 — Baseline is inventory + next-gate specs, not a rewrite

**Choice:** Use this change’s design as the canonical “built vs next” map; OpenSpec specs cover only `production-platform`, `ai-eval-harness`, and `portfolio-baseline`.

**Why:** Config rule says do not bulk-backfill unused areas. Product code for slices 0–7.5 already exists and is documented in `ai.md` / `system.md`.

**Alternative:** Spec every domain as ADDED — rejected (noise, no implementation work).

### D2 — Production topology stays “hosted data + thin VPS compute”

**Choice:** Extend `docker-compose.prod.yml` + scripts; VPS runs api/worker/migrate/nginx; Postgres/Redis/Qdrant/R2 hosted via `.env`. Local `docker-compose.yml` unchanged in behavior.

**Why:** Already locked in `production.md` / `deploy-low.md`; 7P.2 done.

**Alternative:** Self-host DB on VPS — rejected (ops burden; conflicts with existing plan).

### D3 — Storage: document and verify R2 path; keep local volume for dev

**Choice:** 7P.4 is docs + env contract + verification that `get_storage().download(storage_key)` works with `STORAGE_BACKEND=r2` for worker automation. No new storage abstraction.

**Why:** Bytes already behind `get_storage()`; worker must not invent paths.

**Alternative:** Shared NFS between api/worker in prod — rejected (breaks R2 topology).

### D4 — Smoke owns “API process”; evals own “quality process”

| Process | Owns |
|---------|------|
| API (`core.health`, optional `/health/ai`) | Hard deps (Postgres+Redis); soft AI/Qdrant status |
| `scripts/smoke_prod.py` | Deploy gate: health, auth, note create, optional test-search |
| `evals/run_eval.py` | Quality gate: golden cases, tenant isolation |
| GitHub Actions | PR pytest + image build; main → SSH deploy → smoke |

**Why:** Separates deploy readiness from retrieval/LLM quality so CD is not blocked by flaky LLM scores.

**Alternative:** Fold evals into smoke — rejected (LLM latency/cost; false CD failures).

### D5 — Eval tenancy must use real RBAC path

**Choice:** Tenant-isolation cases MUST exercise `WorkspaceVectorSearch` / `GET /ai/test-search` (or chat) with JWT `wid`/`role` — never pass `workspace_id` from query/body.

**Why:** Mirrors `notes/permissions.py` via `build_rbac_filter()`; matches architecture laws.

**Alternative:** Unit-only filter tests — useful as extras, insufficient alone for the C3 gate.

### D6 — Portfolio packaging is docs-first in this repo

**Choice:** README gains pitch, stack, architecture link, built table, metrics placeholders. Live URLs filled when 7P.8 exists. Demo video/Loom is an operator artifact linked from README, not binary in git.

**Why:** Frontend and Loom are outside apply scope; README still unblocks applications once URLs exist.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CD blocked waiting for hosted credentials / VPS | Scripts + workflows land first; gate marked pending until real secrets; local Compose never depends on them |
| Eval flakiness from live LLM | Prefer retrieval/tenant cases for CI-critical path; RAG answer checks optional or thresholded; document honest pass rate |
| Claiming production-ready without smoke | Portfolio spec forbids “production-ready” wording unless smoke/CI evidence exists |
| Scope creep into frontend or Slice 8+ | Explicit non-goals; tasks ordered 7P → evals → README only |
| Soft Qdrant down during smoke | Smoke treats search as optional; `/health` remains db+redis only |

## Migration Plan

1. Land R2 docs + deploy/smoke/CI artifacts on a branch; verify local `docker compose up` still healthy.
2. Run CI on PR (pytest + docker build) with no prod secrets.
3. Provision hosted services + VPS `.env`; run migrate + up + `smoke_prod.py`.
4. Enable CD on `main` after one successful manual deploy.
5. Seed `evals/golden/` against a dedicated workspace; record pass rate in README.
6. Rollback: revert workflow/docs; prod compose is additive — local stack unaffected. No Alembic required unless `/health/ai` needs schema (it does not).

## Open Questions

1. Frontend location for B-gate (sibling repo vs future `frontend/`) — out of apply scope; confirm when starting UI work.
2. Exact VPS host / domain / image registry (GHCR vs Docker Hub) — decide at 7P.5/7P.8 apply time.
3. Whether golden evals run in CI in this change (recommended: local/prod CLI first; CI evals = Phase 2 / follow-up change).
