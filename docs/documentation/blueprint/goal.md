# DashNote AI Engineering — Master Goal & Checklist

> **Extends:** `docs/documentation/blueprint/total.md` (Slices 0–11)  
> **Platform tracker:** `docs/documentation/production.md` (Slice 7P)  
> **Laws:** `docs/documentation/ai.md`, `docs/documentation/rules.md`

## North star

Ship a **multi-tenant, RBAC-safe notes AI** that users trust in production: retrieval that cites real content, agents that mutate data only through services, automation that never acts destructively without review, and deploy gates that catch regressions.

**Philosophy (unchanged):** vertical slices, observable gates, append-only infra, hosted LLM/embeddings only, LangGraph only where tool loops need it.

---

## Master checklist

| Phase | Slice | Goal | Status | Gate doc |
|-------|-------|------|--------|----------|
| 0 | 0 | Foundation — shared contracts | ✅ | `blueprint/total.md` |
| 1 | 1 | Embed pipeline (ARQ + chunk + cache) | ✅ | `blueprint/slice1.md` |
| 2 | 2 | RBAC vector search + Qdrant indexing | ✅ | `blueprint/slice2.md` |
| 3 | 3 | RAG chat MVP | ✅ | `blueprint/slice3.md` |
| 4 | 4 | Streaming + citations polish | ✅ | `blueprint/slice4.md` |
| 5 | 5 | Threads + conversation memory | ✅ | `blueprint/slice5.md` |
| 6 | 6 | LangGraph agent + tools | ✅ | `blueprint/slice6.md` |
| 7 | 7 | Event automation (files, tags, governance) | ✅ | `blueprint/slice7.md` |
| 7.5 | 7.5 | Shared LLM retry + structured layer | ✅ | `blueprint/slice7-llm-hardening.md` |
| **P** | **7P** | **Production platform (VPS + CI/CD)** | **🔄** | `blueprint/slice-platform.md`, `production.md` |
| R | 7R | Retrieval quality + hybrid search | ⬜ | *(this doc §7R)* |
| A | 7A | Automation approval queue (close governance loop) | ⬜ | *(this doc §7A)* |
| 6+ | 6+ | Agent productization (more tools, evals) | ⬜ | *(this doc §6+)* |
| 10 | 10 | AI usage metering + cost visibility | ⬜ | *(this doc §10)* |
| 11 | 11 | Scale — cache, routing, worker scale | ⬜ | `blueprint/total.md` §Slice 11 |
| 8 | 8 | GraphRAG / Neo4j *(optional)* | ⏸ skip until proven need | `blueprint/total.md` §Slice 8 |
| 9 | 9 | Multi-agent supervisor *(late)* | ⏸ skip until proven need | `blueprint/total.md` §Slice 9 |

**Legend:** ✅ done · 🔄 in progress · ⬜ not started · ⏸ deferred

**Hard rule:** Do **not** start **7R, 7A, 6+, 10, 11, 8, or 9** until **7P.8** passes on a real VPS.

---

## Execution order (recommended)

```
7P.4 → 7P.8   Production gate (blocking)
    ↓
7R            Retrieval quality + hybrid + file-aware RAG
    ↓
7A            Automation human-approval queue
    ↓
6+            Agent tools + agent evals
    ↓
10            Usage / cost metering
    ↓
11            Caching + model routing + worker scale
    ↓
8, 9          Only if product demands it
```

---

## Slice 7P — Production platform *(in progress)*

Detail: `docs/documentation/production.md` · Prompts: `docs/documentation/blueprint/slice-platform.md`

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 7P.0 | Discovery audit | ✅ | Blockers report |
| pre-7P.1 | Soft Qdrant boot + gitignore | ✅ | `main.py`, `worker/main.py` |
| 7P.1 | Env contract | ✅ | `.env.example`, `.env.production.example` |
| 7P.2 | Prod compose | ✅ | `docker-compose.prod.yml` |
| 7P.3 | Soft dependency boot | ✅ | Qdrant try/except at startup |
| 7P.4 | Storage contract (R2) | ⬜ | R2 vars documented; dev stays `local` + volume |
| 7P.5 | Deploy scripts + runbook | ⬜ | `scripts/deploy/*`, deployment runbook |
| 7P.6 | Health + smoke | ⬜ | `scripts/smoke_prod.py`, optional `GET /health/ai` |
| 7P.7 | CI (PR) | ⬜ | `.github/workflows/ci.yml` — pytest + docker build |
| 7P.8 | CD + VPS gate | ⬜ | `.github/workflows/deploy.yml`, production smoke PASS |

### Gate (7P.8)

```powershell
curl https://api.<domain>/health                          # 200, db + redis ok
$env:SMOKE_BASE_URL="https://api.<domain>"; python scripts/smoke_prod.py
python scripts/e2e_agent_test.py --base-url https://api.<domain>
```

---

## Slice 7R — Retrieval quality *(new — extends Slice 2)*

**Goal:** Measurable retrieval quality before adding graph or multi-agent complexity.

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 7R.1 | Golden eval set | ⬜ | `tests/ai/fixtures/retrieval_golden.json` + seeded workspace |
| 7R.2 | Eval runner | ⬜ | `scripts/eval_retrieval.py` — recall@k, RBAC leak check |
| 7R.3 | Hybrid search | ⬜ | Sparse/BM25 or Qdrant hybrid in `ai/retrieval/` |
| 7R.4 | Unified notes + files RAG | ⬜ | `RagService` merges `notes_chunks` + `files_chunks` |
| 7R.5 | Re-index tooling | ⬜ | `scripts/reindex_workspace.py` for payload/chunk changes |
| 7R.6 | CI hook | ⬜ | Eval runner in CI (or nightly) against test fixtures |

### Gate (7R)

- [ ] Golden set: ≥ **80%** recall@5 on seeded notes (owner + member roles)
- [ ] Member role: **zero** private notes from other users in results
- [ ] File upload: question about file content returns citation with `file_id`
- [ ] `python scripts/eval_retrieval.py` exits 0

### Laws (carry forward)

- `workspace_id` from JWT only — never query/body
- `WorkspaceVectorSearch` only — no raw Qdrant in routers
- `build_rbac_filter()` mirrors `notes/permissions.py`

---

## Slice 7A — Automation approval queue *(new — extends Slice 7.4)*

**Goal:** Close the governance loop — blocked destructive actions surface for human review instead of disappearing in logs.

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 7A.1 | DB migration | ⬜ | `automation_pending_actions` table |
| 7A.2 | Repository + service | ⬜ | `worker/automation/` or new `automation/` module |
| 7A.3 | `store_pending_action()` | ⬜ | Wire `AutomationDecisionEngine` block path |
| 7A.4 | HTTP routes | ⬜ | `GET /automation/pending`, `POST .../approve`, `POST .../reject` |
| 7A.5 | First real automation | ⬜ | e.g. duplicate-note detection → merge suggestion |
| 7A.6 | Tests | ⬜ | Governance block → row in DB → approve executes via service |

### Gate (7A)

- [ ] Blocked action logs `[AUTOMATION_GOVERNANCE_BLOCK]` **and** creates pending row
- [ ] Owner/admin can list pending actions scoped to `workspace_id`
- [ ] Approve runs mutation through **service layer** (not repository shortcut)
- [ ] Reject leaves data unchanged

### Laws

- `AutomationDecisionEngine` import law unchanged (no FastAPI/SQLAlchemy in `decision.py`)
- Additive tasks (`generate_note_tags`, `index_file_chunks`, etc.) **never** call governance

---

## Slice 6+ — Agent productization *(extends Slice 6)*

**Goal:** Make the workspace assistant useful daily — more tools, grounded answers, eval coverage.

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 6+.1 | `search_files` tool | ⬜ | Retrieval over `files_chunks` with RBAC |
| 6+.2 | `list_notebooks` / notebook context | ⬜ | Optional — if notebooks are first-class in UX |
| 6+.3 | Tool policy per role | ⬜ | Config or workspace setting to disable mutations for `member` |
| 6+.4 | Grounding rule in prompts | ⬜ | Agent must cite retrieval when stating facts |
| 6+.5 | Agent eval scenarios | ⬜ | Extend `scripts/e2e_agent_test.py` — multi-step flows |
| 6+.6 | Stream UX events | ⬜ | `tool_start` / `tool_end` stable for frontend |

### Gate (6+)

- [ ] `POST /ai/agent` — "summarize workspace and create a note" → note exists in DB
- [ ] Cross-workspace thread/note access returns **404**, never leaks data
- [ ] `python scripts/e2e_agent_test.py` passes against prod smoke URL
- [ ] `/ai/chat*` unchanged — fast RAG path still works

### Laws

- Tools → `NoteService` / `RagService` only
- `db_session_var` set in graph tool node before mutations
- Coexistence: never replace `/ai/chat*` with agent-only

---

## Slice 10 — Observability & cost *(extends blueprint Slice 10)*

**Goal:** Workspace-visible AI cost and quality signals — not only Langfuse for engineers.

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 10.1 | `ai_usage` table | ⬜ | Alembic migration — tokens, model, cost_usd, operation |
| 10.2 | Usage recorder | ⬜ | Hook in `RagService`, agent `call_model`, automation LLM calls |
| 10.3 | Workspace usage API | ⬜ | `GET /ai/usage` — owner/admin, date range |
| 10.4 | Prometheus AI counters | ⬜ | `dashnote_ai_*` — retrieval latency, embed queue depth |
| 10.5 | Alert markers doc | ⬜ | Runbook for `[AUTOMATION_LLM_RETRY_EXHAUSTED]`, Qdrant down |

### Gate (10)

- [ ] Each `/ai/chat` call writes one `ai_usage` row with token counts
- [ ] Owner can query usage for their workspace (last 30 days)
- [ ] Grafana folder **DashNote** has at least one AI panel (or Grafana Cloud equivalent)

---

## Slice 11 — Scale & economics

Detail: `docs/documentation/blueprint/total.md` §Slice 11

| Step | Task | Status | Key outputs |
|------|------|--------|-------------|
| 11.1 | RAG response cache | ⬜ | Redis keyed by `workspace_id` + question hash + gen counter |
| 11.2 | Model routing | ⬜ | Cheap model for classify/summarize; expensive for agent reasoning |
| 11.3 | Worker horizontal scale | ⬜ | `docker compose up --scale worker=N` documented + `WORKER_MAX_JOBS` tuned |
| 11.4 | Embed batch tuning | ⬜ | `EMBEDDING_BATCH_SIZE` vs provider TPM documented |

### Gate (11)

- [ ] Repeated identical RAG question hits cache (verify via Redis `GET`)
- [ ] Cache invalidates on note write (generation counter bump)
- [ ] 3 workers process concurrent embed jobs without rate-limit storm

---

## Slice 8 — GraphRAG *(optional — defer)*

**Start only when all are true:**

- [ ] 7P.8 production gate passed
- [ ] 7R eval gate passed in production traffic
- [ ] Users explicitly need "related notes" / relationship traversal
- [ ] Product sign-off that vector search is insufficient

Detail: `docs/documentation/blueprint/total.md` §Slice 8

---

## Slice 9 — Multi-agent *(optional — defer)*

**Start only when:**

- [ ] Slice 6+ stable in production
- [ ] Concrete product requirement single-agent cannot meet
- [ ] Intent routing eval set exists

Detail: `docs/documentation/blueprint/total.md` §Slice 9

---

## Cross-cutting checklist (every slice)

| Rule | Enforced in |
|------|-------------|
| `workspace_id` from `RequestContext` / JWT only | Routers, retrieval, indexing |
| RBAC filter on every Qdrant query | `ai/retrieval/filters.py` |
| Freeze ctx → primitives before SSE generators | `ai_routes/chat.py`, `agent.py` |
| Tools → services → repositories | `ai/tools/`, `notes/service.py` |
| Prompts only in `ai/prompts/` | RAG, agent, automation |
| Structured LLM outputs for automation | `shared/llm/structured.py` |
| Append-only infra (`compose`, `requirements`, `config`) | All slices |
| Gate script or pytest before next slice | This doc + per-slice blueprint |

---

## Validation commands (quick reference)

```powershell
# Unit / integration
python -m pytest tests/shared/test_llm_structured.py tests/worker/test_automation_decision.py -q
python -m pytest tests/ai/test_agent_retry.py -q

# Local stack
docker compose up -d --build
curl.exe -sS http://127.0.0.1/health

# AI smoke (local)
python scripts/e2e_agent_test.py

# Retrieval test (manual until 7R.2)
curl.exe -sS -H "Authorization: Bearer <token>" "http://127.0.0.1/ai/test-search?q=your+query&limit=5"

# Prod gate (after 7P.8)
python scripts/smoke_prod.py
```

---

## Related docs

| Doc | Use when |
|-----|----------|
| `docs/documentation/blueprint/total.md` | Original slice architecture + build history |
| `docs/documentation/production.md` | 7P step-by-step status |
| `docs/documentation/ai.md` | AI module laws and HTTP contracts |
| `docs/documentation/rules.md` | Import direction, Slice 6 modification laws |
| `docs/documentation/observe.md` | Tracing and metrics validation |
| `docs/documentation/lld.md` | Low-level design §4.12–4.18 |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-30 | Initial `goal.md` — extends blueprint with 7R, 7A, 6+, reordered 10/11 before 8/9 |
