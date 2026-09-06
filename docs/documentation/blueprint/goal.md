# DashNote — Job Search Baseline Checklist

> **Locked path:** Follow [`../blueprint8.md`](../blueprint8.md) first (Alive + Tier 0/1/2). This file is the checkbox tracker under that lock.  
> **Purpose:** Finish this checklist, **then** start applying for remote AI engineer roles and freelance RAG/LLM work.  
> **Detail:** Day-by-day plan in [`docs/ship-plan.md`](../../ship-plan.md) · Platform steps in [`production.md`](../production.md) · Slice 8X detail index [`slice8_X.md`](slice8_X.md) · Full slice roadmap in [`total.md`](total.md)

---

## When you are allowed to job search

**Start applying only when every box in §Job-search gate passes.**

Until then, you have a strong backend portfolio — not a hireable story. Recruiters and clients need a **live URL**, **proof you can demo in 2 minutes**, and **one measurable quality signal** (eval pass rate or cost/latency table).

| Track | Baseline target | After baseline |
|-------|-----------------|----------------|
| **Remote AI engineer** (employment) | Top ~10% portfolio — live product + CI + evals + demo video | Phase 2 / blueprint8 Tier 1–2 → top ~3–5% |
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
| A1 | Hosted services provisioned (Postgres, Redis, Qdrant Cloud, R2 or equiv.) | ⬜ | Credentials in VPS `.env` only — operator confirm |
| A2 | **7P.4** R2/storage — worker reads uploads without local volume | ✅ | Documented in `.env.production.example` + `docs/deployment/storage.md` |
| A3 | **7P.5** Deploy scripts + runbook | ✅ | `scripts/deploy/*`, `docs/deployment/runbook.md` |
| A4 | **7P.6** `scripts/smoke_prod.py` passes on prod URL | ⬜ | Local `http://127.0.0.1` smoke PASS (2026-09-06); **HTTPS prod still required** |
| A5 | **7P.7** CI green on PR (`pytest` + docker build) | ✅ | `.github/workflows/ci.yml` |
| A6 | **7P.8** CD workflow + gate docs | ✅ | `.github/workflows/deploy.yml` (live VPS proof still needed for A4/A7 claim) |
| A7 | TLS live API | ⬜ | `https://api.<domain>/health` → 200 — need prod URL |

```powershell
# A-gate commands
curl.exe -sS https://api.<domain>/health
$env:SMOKE_BASE_URL="https://api.<domain>"; python scripts/smoke_prod.py
python scripts/e2e_agent_test.py --base-url https://api.<domain>
```

---

### B — Frontend (live product)

Build against the API using **[frontendguide.md](../frontendguide.md)** (auth, domain routes, SSE citations, CORS, B1–B7).

| # | Task | Status | Output |
|---|------|--------|--------|
| B1 | Auth: register, login, Bearer on API calls | ✅ | Sibling `dashnotes` Playwright `b-gate.spec.ts` vs local API (2026-09-06) |
| B2 | Notes CRUD + file upload UI | ✅ | Same B-gate e2e |
| B3 | Chat UI: SSE stream + citations from `metadata` event | ✅ | B-gate e2e (tolerates AI-down path) |
| B4 | Threads sidebar + history | ⬜ | Not asserted in current B-gate e2e |
| B5 | Agent view (optional but strong): tool_start / tool_end | ✅ | B-gate navigates agent + run |
| B6 | Error UX: 503 LLM down, 429 rate limit | ✅ | B-gate accepts AI-unavailable copy |
| B7 | Frontend deployed with TLS | ⬜ | `https://app.<domain>` — pending |

**Demo gate (record on video):** register → create note → upload file → RAG question with citation → agent creates/updates note.

---

### C — Evaluation (interview differentiator)

| # | Task | Status | Output |
|---|------|--------|--------|
| C1 | `evals/golden/` — ≥10 cases (retrieval + tenant isolation) | ✅ | 10 retrieval + 5 tenant JSONL cases |
| C2 | `evals/run_eval.py` — pass/fail summary CLI | ✅ | fixture + live; `PASS: X/Y` |
| C3 | Tenant isolation case: member cannot retrieve peer's private note | ✅ | Fixture automated; live dual-token via `--token-b` |
| C4 | Eval pass rate ≥ **80%** documented in README | ✅ | Fixture **15/15**; live local **8/8** (see `evals/README.md` / root README) |

```powershell
python evals/run_eval.py --base-url https://api.<domain> --token <token>
```

**Minimum for job search:** C1–C4. Hybrid search, recall@k CI gates, agent evals → **after** you land interviews (ship-plan Phase 2).

---

### D — Portfolio packaging (recruiter / client ready)

| # | Task | Status | Output |
|---|------|--------|--------|
| D1 | README: pitch, live links, stack, architecture diagram link | ✅ | `readme.md` — prod URLs explicit pending |
| D2 | Screenshots or GIF on README | ⬜ | Chat + citations visible |
| D3 | **3-minute demo video** (Loom / YouTube unlisted) | ⬜ | Link in README |
| D4 | Cost + latency table (even rough) | ⬜ | Placeholder in README — fill from Langfuse / sample |
| D5 | GitHub topics: `rag`, `langgraph`, `fastapi`, `qdrant` | ⬜ | Set on remote when `gh`/UI available |
| D6 | `docs/interview-talk-track.md` — 2-min pitch + 3 tradeoffs | ✅ | Interview prep |

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
[x] A2 Storage contract (R2)
[x] A3 Deploy scripts + runbook
[ ] A4 smoke_prod.py PASS on prod (local PASS 2026-09-06)
[x] A5 CI green on PR
[x] A6 CD workflow + gate docs (live VPS proof still open)
[ ] A7 https://api.<domain>/health → 200

FRONTEND
[x] B1 Auth + CORS (local Playwright B-gate)
[x] B2 Notes + file upload
[x] B3 Chat SSE + citations
[ ] B4 Threads
[x] B5 Agent UI (recommended)
[x] B6 Error states
[ ] B7 https://app.<domain> live

EVALUATION
[x] C1 ≥10 golden cases
[x] C2 run_eval.py CLI
[x] C3 Tenant isolation automated
[x] C4 ≥80% pass rate in README

PORTFOLIO
[x] D1 README with live links / pending honesty
[ ] D2 Screenshots/GIF
[ ] D3 Demo video
[ ] D4 Cost/latency table
[ ] D5 GitHub topics
[x] D6 Interview talk track

FREELANCE (one of)
[ ] Tier B: all above
[ ] Tier A: Lite demo URL + template + Loom
```

**→ When every checked item you need for your track is done: start job search.**

---

## Recommended order

### Preferred — Blueprint 8 (operator default) + Slice 8X detail

Follow [`../blueprint8.md`](../blueprint8.md) for Alive + Tier map. Execute Composer substages via [`slice8_X.md`](slice8_X.md) (index). Live URL first; evals after VPS (still required for C-gate):

1. **A5 / 8X.1** — thin CI ([`slice8_ci.md`](slice8_ci.md))
2. **A1–A4, A6–A7 / 8X.4** — finish platform + live smoke (7P.4–7P.6, 7P.8)
3. **B1–B7 / 8X.5** — frontend ([`frontendguide.md`](../frontendguide.md))
4. **C1–C4 / 8X.2** — evals ([`slice8_eval.md`](slice8_eval.md); prefer `--base-url` against prod)
5. **8X.3** — HITL API ([`slice8_hitl.md`](slice8_hitl.md); HITL UX after API exists) — Tier 1
6. **D1–D6** — portfolio packaging
7. **Tier 1–2 deepeners** — Langfuse depth, fixture CI, EXPERIMENTS / recall / faithfulness per blueprint8 (while interviewing)

### Alternate — AI-depth-first (harness before URL)

Use only when interview harness depth matters more than a public URL this week:

1. **A5 / 8X.1** — thin CI
2. **C1–C4 / 8X.2** — evals
3. **8X.3** — HITL API
4. **A1–A4, A6–A7 / 8X.4** — finish platform + live smoke
5. **B1–B7 / 8X.5** — frontend (+ HITL UX after 8X.3)
6. **D1–D6** — portfolio packaging

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
| [`slice8_X.md`](slice8_X.md) | **Preferred ship path index (deploy-first):** CI → finish prod → FE → evals → HITL |
| [`slice8_ci.md`](slice8_ci.md) / [`slice8_eval.md`](slice8_eval.md) / [`slice8_hitl.md`](slice8_hitl.md) | Detail substep prompts (option B) |
| [`production.md`](../production.md) | 7P step status tracker |
| [`total.md`](total.md) | Full slice architecture (0–11) |
| [`ai.md`](../ai.md) | AI module laws |
| [`ship-plan.md` §Two tiers](../../ship-plan.md) | Lite vs Full freelance pricing |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-03 | Added preferred **Slice 8X** order; kept alternate “fastest live URL” short-order |
| 2026-06-30 | Initial extended roadmap (7R, 7A, 6+, …) |
| 2026-06-30 | **Rewritten** — job-search baseline gate; deferred post-hire slices |
