# DashNote — Job Search Baseline Checklist

> **Purpose:** Finish this checklist, **then** start applying for remote AI engineer roles and freelance RAG/LLM work.  
> **Detail:** Day-by-day plan in [`docs/ship-plan.md`](../../ship-plan.md) · Platform steps in [`production.md`](../production.md) · Full slice roadmap in [`total.md`](total.md)

---

## When you are allowed to job search

**Start applying only when every box in §Job-search gate passes.**

Until then, you have a strong backend portfolio — not a hireable story. Recruiters and clients need a **live URL**, **proof you can demo in 2 minutes**, and **one measurable quality signal** (eval pass rate or cost/latency table).

| Track | Baseline target | After baseline |
|-------|-----------------|----------------|
| **Remote AI engineer** (employment) | Top ~10% portfolio — live product + CI + evals + demo video | Phase 2 in ship-plan → top ~3–5% |
| **Freelance / Upwork** | Tier A Lite demo **or** Tier B DashNote live URL + Loom | Lite for <$2k jobs; DashNote for $5k+ |

---

## Already done (do not rebuild)

Backend AI slices **0 → 7.5** are complete. This is your competitive advantage — most applicants stop at a tutorial RAG.

| Area | Status | Proof |
|------|--------|-------|
| Embed pipeline (ARQ, chunk, cache) | ✅ | Slice 1 |
| RBAC vector search + Qdrant | ✅ | Slice 2, `GET /ai/test-search` |
| RAG chat + SSE + citations | ✅ | `POST /ai/chat`, `/stream` |
| Threads + memory | ✅ | `GET /ai/threads` |
| LangGraph agent + tools | ✅ | `POST /ai/agent`, `e2e_agent_test.py` |
| File automation + governance | ✅ | Slice 7, `AutomationDecisionEngine` |
| LLM retry + structured layer | ✅ | `shared/llm/` |
| Architecture docs + laws | ✅ | `ai.md`, `rules.md`, `lld.md` |
| Local Docker full stack | ✅ | `docker compose up` |
| Langfuse + Prometheus design | ✅ | `observe.md` |

**You are not starting from zero.** The baseline is **ship + show + measure**, not more backend slices.

---

## Job-search gate (all required)

Copy this section into your tracker. Check each item. **All must be ✅ before job search.**

### A — Production (Slice 7P)

| # | Task | Status | Output |
|---|------|--------|--------|
| A1 | Hosted services provisioned (Postgres, Redis, Qdrant Cloud, R2 or equiv.) | ⬜ | Credentials in VPS `.env` only |
| A2 | **7P.4** R2/storage — worker reads uploads without local volume | ⬜ | Documented in `.env.production.example` |
| A3 | **7P.5** Deploy scripts + runbook | ⬜ | `scripts/deploy/*`, `docs/deployment/runbook.md` |
| A4 | **7P.6** `scripts/smoke_prod.py` passes on prod URL | ⬜ | health + auth + note + optional search |
| A5 | **7P.7** CI green on PR (`pytest` + docker build) | ⬜ | `.github/workflows/ci.yml` |
| A6 | **7P.8** CD deploys `main` → VPS; smoke exits 0 | ⬜ | `.github/workflows/deploy.yml` |
| A7 | TLS live API | ⬜ | `https://api.<domain>/health` → 200 |

```powershell
# A-gate commands
curl.exe -sS https://api.<domain>/health
$env:SMOKE_BASE_URL="https://api.<domain>"; python scripts/smoke_prod.py
python scripts/e2e_agent_test.py --base-url https://api.<domain>
```

---

### B — Frontend (live product)

| # | Task | Status | Output |
|---|------|--------|--------|
| B1 | Auth: register, login, Bearer on API calls | ⬜ | No CORS errors vs prod API |
| B2 | Notes CRUD + file upload UI | ⬜ | Upload → ~45s → metadata visible |
| B3 | Chat UI: SSE stream + citations from `metadata` event | ⬜ | Grounded answer with sources |
| B4 | Threads sidebar + history | ⬜ | Continue prior conversation |
| B5 | Agent view (optional but strong): tool_start / tool_end | ⬜ | Multi-step demo works |
| B6 | Error UX: 503 LLM down, 429 rate limit | ⬜ | User-visible messages |
| B7 | Frontend deployed with TLS | ⬜ | `https://app.<domain>` |

**Demo gate (record on video):** register → create note → upload file → RAG question with citation → agent creates/updates note.

---

### C — Evaluation (interview differentiator)

| # | Task | Status | Output |
|---|------|--------|--------|
| C1 | `evals/golden/` — ≥10 cases (retrieval + tenant isolation) | ⬜ | `retrieval.jsonl`, `tenant_isolation.jsonl` |
| C2 | `evals/run_eval.py` — pass/fail summary CLI | ⬜ | `PASS: 8/10` or better |
| C3 | Tenant isolation case: member cannot retrieve peer's private note | ⬜ | Automated check in runner |
| C4 | Eval pass rate ≥ **80%** documented in README | ⬜ | Honest score if not 100% |

```powershell
python evals/run_eval.py --base-url https://api.<domain> --token <token>
```

**Minimum for job search:** C1–C4. Hybrid search, recall@k CI gates, agent evals → **after** you land interviews (ship-plan Phase 2).

---

### D — Portfolio packaging (recruiter / client ready)

| # | Task | Status | Output |
|---|------|--------|--------|
| D1 | README: pitch, live links, stack, architecture diagram link | ⬜ | `readme.md` |
| D2 | Screenshots or GIF on README | ⬜ | Chat + citations visible |
| D3 | **3-minute demo video** (Loom / YouTube unlisted) | ⬜ | Link in README |
| D4 | Cost + latency table (even rough) | ⬜ | Langfuse export or 20-request sample |
| D5 | GitHub topics: `rag`, `langgraph`, `fastapi`, `qdrant` | ⬜ | Repo discoverability |
| D6 | `docs/interview-talk-track.md` — 2-min pitch + 3 tradeoffs | ⬜ | Interview prep |

**Stranger test:** Someone unfamiliar opens README → uses live app in **<2 minutes** without your help.

---

### E — Freelance-only (pick one path)

| Path | Required for Upwork baseline | Status |
|------|------------------------------|--------|
| **Tier B** (DashNote-class, $5k+) | A + B + C + D all ✅ | ⬜ |
| **Tier A** (Lite RAG, $800–3.5k) | Separate Lite demo URL + `templates/lite-gpt-rag` + 2-min Loom | ⬜ |

Do **not** sell Tier B scope at Tier A price. See [`ship-plan.md`](../../ship-plan.md) §Two tiers.

---

## Job-search gate — single checklist

```
PRODUCTION
[ ] A1 Hosted services live
[ ] A2 Storage contract (R2)
[ ] A3 Deploy scripts + runbook
[ ] A4 smoke_prod.py PASS on prod
[ ] A5 CI green on PR
[ ] A6 CD deploy + smoke on merge
[ ] A7 https://api.<domain>/health → 200

FRONTEND
[ ] B1 Auth + CORS
[ ] B2 Notes + file upload
[ ] B3 Chat SSE + citations
[ ] B4 Threads
[ ] B5 Agent UI (recommended)
[ ] B6 Error states
[ ] B7 https://app.<domain> live

EVALUATION
[ ] C1 ≥10 golden cases
[ ] C2 run_eval.py CLI
[ ] C3 Tenant isolation automated
[ ] C4 ≥80% pass rate in README

PORTFOLIO
[ ] D1 README with live links
[ ] D2 Screenshots/GIF
[ ] D3 Demo video
[ ] D4 Cost/latency table
[ ] D5 GitHub topics
[ ] D6 Interview talk track

FREELANCE (one of)
[ ] Tier B: all above
[ ] Tier A: Lite demo URL + template + Loom
```

**→ When every checked item you need for your track is done: start job search.**

---

## Recommended order (when time is short)

1. **A4 + A7** — prod API + smoke (blocks everything)
2. **B1–B3 + B7** — minimum UI to demo RAG
3. **D1 + D3** — README + video (apply while finishing C)
4. **C1–C4** — evals (strongest interview ammo)
5. **A5–A6** — CI/CD (signals maturity)
6. **B4–B6, D2, D4–D6** — polish before heavy interviewing

---

## Explicitly NOT required for job-search baseline

Finish these **after** you are applying or employed — do not block job search on them.

| Slice | Why defer |
|-------|-----------|
| 7A Automation approval queue | No client asks in first interview |
| 6+ Extra agent tools | Agent already works; demo beats breadth |
| 7R hybrid search / reranker | Nice for Phase 2 article; evals matter more first |
| 10 `ai_usage` metering API | Langfuse cost snapshot is enough for baseline |
| 11 Scale / RAG cache | Post-traffic problem |
| 8 GraphRAG / Neo4j | Optional forever unless product demands |
| 9 Multi-agent | Late stage only |

---

## Post-baseline (Phase 2 — while interviewing)

Improves offer rate and rate negotiation; not a blocker to **first** applications.

| Item | Target | Doc |
|------|--------|-----|
| Evals in CI | Bad PR fails merge | ship-plan Day 15–28 |
| recall@5 ≥ 0.8 | Quantified retrieval story | Slice 7R |
| Agent eval scenarios ≥5 | Tool-use proof | ship-plan Phase 2 |
| Public technical article | LinkedIn + dev.to | ship-plan Day 36–45 |
| Runbook + rollback tested | “Production-ready” claim | 7P.5 |
| Lite template clone | Fast Upwork turnaround | ship-plan §Lite |

---

## What to say when you apply

### Remote AI engineer (employment)

**Headline:** Multi-tenant RAG + LangGraph agent platform — live demo, eval suite, prod on VPS.

**3 bullets for resume:**
- Built RBAC-aware vector retrieval (Qdrant) mirroring app permissions — tenant isolation tested in eval harness
- Shipped RAG chat (SSE + citations) and LangGraph workspace agent with tool mutations via service layer
- Production stack: FastAPI, ARQ workers, LiteLLM, Langfuse tracing, Docker CI/CD to VPS

**Link order in application:** Demo video → Live app → GitHub → eval pass rate in README

### Freelance (Upwork / direct client)

**Tier A pitch:** “Custom RAG chatbot on your documents — deployed in ~1 week with citations.”  
**Tier B pitch:** “Same engineer behind [live DashNote URL] — multi-tenant, agents, workers, observability.”

Attach **Phase 2 upgrade quote** on every Lite delivery.

---

## Success metrics (fill when baseline complete)

| Metric | Target | Actual | Date |
|--------|--------|--------|------|
| Live app URL | ✅ | | |
| Live API URL | ✅ | | |
| smoke_prod.py | PASS | | |
| CI on PR | green | | |
| Golden eval pass rate | ≥80% | | |
| Demo video | linked | | |
| Stranger test | <2 min to demo | | |
| **Job search started** | ✅ | | |

---

## Related docs

| Doc | Use |
|-----|-----|
| [`ship-plan.md`](../../ship-plan.md) | 14-day / 45-day day-by-day tasks |
| [`production.md`](../production.md) | 7P step status tracker |
| [`total.md`](total.md) | Full slice architecture (0–11) |
| [`ai.md`](../ai.md) | AI module laws |
| [`ship-plan.md` §Two tiers](../../ship-plan.md) | Lite vs Full freelance pricing |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-30 | Initial extended roadmap (7R, 7A, 6+, …) |
| 2026-06-30 | **Rewritten** — job-search baseline gate; deferred post-hire slices |
