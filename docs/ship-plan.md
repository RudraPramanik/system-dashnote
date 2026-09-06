# DashNote Ship Plan — Top 10% (14 days) → Top 3–5% (45 days)

> **Locked path:** Follow [`docs/documentation/blueprint8.md`](documentation/blueprint8.md) first (Alive law + Tier 0 job gate + Tier 1/2 deepeners).  
> This ship-plan is the day-by-day checklist under that lock. Detail Composer prompts: [`documentation/blueprint/slice8_X.md`](documentation/blueprint/slice8_X.md).  
> **7P truth:** [`documentation/production.md`](documentation/production.md) (do not trust stale Day-0 rows over the tracker).

**Purpose:** Actionable checklist to turn this repo from a strong backend portfolio into a hiring-manager-ready AI product. Aligns with existing platform work in [`docs/documentation/production.md`](documentation/production.md) (slice **7P**) and observability in [`docs/observability.md`](observability.md).

**Related docs:** [Blueprint 8 (default)](documentation/blueprint8.md) · [system](documentation/system.md) · [AI architecture](documentation/ai.md) · [LLD](documentation/lld.md) · [UML diagrams](uml/diagrams.md) · [deploy laws](documentation/deploy-low.md)

---

## Current baseline (Day 0)

| Strength | Gap |
|----------|-----|
| Multi-tenant RAG + LangGraph agent + worker automation | Live product URL / stranger demo still to prove (goal B + smoke) |
| Langfuse traces, Prometheus, Grafana | Eval harness + cost SLO doc still thin (goal C / D4) |
| Excellent internal docs + architecture laws | AI path test coverage thin |
| Docker Compose local stack | Frontend ↔ prod wiring / TLS demo path |
| E2E scripts (`scripts/e2e_agent_test.py`) | HITL + Langfuse retrieval-depth (Tier 1) not done |
| CI/CD workflows present (see `production.md` 7P.7–7P.8) | Claim production-live only after VPS smoke proof |

**Phase 1 = Blueprint8 Tier 0** (job gate → top ~10%). **Phase 2 = Tier 1 then Tier 2** (HITL, Langfuse depth, fixture CI, experiments / recall / faithfulness → top ~3–5%).

**Target after 14 days:** Recruiter clicks live app in 30s; tech lead sees CI, prod, evals, cost — **top ~10%** of mid-level AI engineer portfolios.

**Target after 45 days:** Regression-gated quality, production ops story, differentiated depth — **top ~3–5%**.

---

## Two tiers — full stack vs simple GPT wrapper (Upwork)

You run **two deliverables**, not one. DashNote is the **premium proof**; a **Lite template** lets you win low-budget jobs fast without falling behind “production-ready GPT” freelancers who ship less underneath.

```
                    ┌─────────────────────────────────────┐
                    │         Client conversation          │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
     ┌─────────────────┐                           ┌─────────────────┐
     │  Tier A — Lite  │                           │ Tier B — Full   │
     │  GPT + RAG MVP  │                           │ DashNote-class  │
     │  $800–3,500     │                           │ $5,000–18,000+  │
     └─────────────────┘                           └─────────────────┘
              │                                               │
              │         upgrade path (Phase 2 contract)       │
              └──────────────────►────────────────────────────┘
```

### When to sell which tier

| Signal from client | Tier | Your pitch |
|--------------------|------|------------|
| Budget **<$2k**, “chatbot on my PDFs”, 1 user or internal tool | **A — Lite** | “Custom GPT on your docs — live in ~1 week” |
| “Just need ChatGPT on our website” | **A — Lite** | Same; set expectations: no multi-tenant SaaS |
| Multiple users, login, teams, permissions | **B — Full** | Point to DashNote demo |
| “Production”, compliance, audit, SLA | **B — Full** | RBAC search, workers, observability |
| Already bought Lite from you; needs auth + teams | **A → B upgrade** | Fixed migration quote |

**Rule:** Never build Tier B scope at Tier A price. Never oversell Lite as “enterprise multi-tenant.”

---

### Tier A — Simple GPT wrapper (Lite stack)

**Goal:** Ship in **3–7 days**. Same *outcome* clients see on Upwork (upload docs → ask questions), minimal moving parts.

#### Lite architecture (default recipe)

Use your **Next.js** strength — most Lite jobs never need the full DashNote repo.

```
User (browser)
    ▼
Next.js app (Vercel / Cloudflare Pages)
    ├── /chat          UI (React, Tailwind — your 4 yr stack)
    ├── /api/chat      Route Handler → OpenAI / LiteLLM chat + tools optional
    └── /api/upload    Route Handler → extract text → embed → upsert vectors
    ▼
Vector store (pick one per job)
    ├── Qdrant Cloud free tier     (closest to DashNote; reuse mental model)
    ├── Pinecone serverless        (client name recognition)
    └── Supabase pgvector          (if client already on Supabase)
    ▼
LLM
    └── OpenAI gpt-4o-mini OR Gemini flash (cost-sensitive clients)
```

**Optional Lite backend** (when client forbids serverless limits): single **`lite-api/`** folder — slim FastAPI (~300–500 LOC), one `workspace_id` constant or simple API key, no ARQ worker (sync embed on upload or Vercel background function).

#### Lite — in scope / out of scope

| In scope (promise this) | Out of scope (upsell to Tier B) |
|-------------------------|----------------------------------|
| Chat UI + streaming | Multi-tenant workspaces + JWT RBAC |
| Upload PDF/TXT/DOCX → Q&A | LangGraph agent + tool mutations |
| Basic RAG (chunk, embed, top-k, cite filenames) | Permission-aware vector filters |
| One API key or simple password gate | Worker queue + automation |
| Deploy to Vercel + env vars doc | Langfuse/Grafana/Prometheus |
| 7-day bug-fix window | Eval harness + CI regression |

#### Lite — file template (build once, clone per client)

Keep a separate repo or `templates/lite-gpt-rag/`:

```
templates/lite-gpt-rag/
├── README.md              # handoff for client
├── .env.example           # OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY
├── app/
│   ├── page.tsx           # chat
│   ├── api/chat/route.ts
│   └── api/upload/route.ts
├── lib/
│   ├── chunk.ts           # ~500 char chunks, overlap 100
│   ├── embed.ts           # openai embeddings or litellm
│   ├── vector.ts          # qdrant upsert/search wrapper
│   └── prompts.ts         # system prompt + “answer only from context”
└── scripts/smoke.mjs      # one upload + one question
```

**Reuse from DashNote knowledge (without importing the repo):** chunk overlap habits, “citations from retrieved chunks not stream”, score threshold ~0.4, system prompt structure from `src/ai/prompts/rag.py` — reimplemented in ~50 lines for Lite.

#### Lite — delivery checklist (per client)

- [ ] Client provides docs or sample files
- [ ] Collection name = `{client_slug}_docs`
- [ ] Upload → embed → chat works on **production URL**
- [ ] README: env vars, how to add files, estimated OpenAI cost/month
- [ ] Loom **2 min** walkthrough (counts as “production-ready” for this tier)
- [ ] Invoice line: “Phase 1 Lite” — optional “Phase 2 Full platform” quote attached

#### Lite — pricing (Bangladesh / Upwork — win jobs, don’t race to $5/hr)

| Package | Scope | Fixed price | Your effort |
|---------|-------|-------------|-------------|
| **Lite S** | Chat + 1 data source, no auth | **$800–1,200** | 2–3 days |
| **Lite M** | Chat + upload UI + password | **$1,200–2,000** | 4–5 days |
| **Lite L** | Lite M + branding + 2 file types + deploy | **$2,000–3,500** | 5–7 days |

Hourly equivalent target: **$35–50/hr** effective (acceptable for volume + reviews).  
**After 3 Lite reviews:** raise Lite L to **$2,500–4,000**.

#### Lite — honest Upwork copy (don’t undersell, don’t lie)

**Say:** “Custom RAG chatbot on your documents — deployed, with citations and upload UI.”  
**Don’t say:** “Enterprise multi-tenant AI platform.”  
**Optional footnote:** “Built by the same engineer who ships [DashNote live URL] for teams needing auth, agents, and ops.”

---

### Tier B — Full stack (this repo — DashNote-class)

Reference: [`system.md`](documentation/system.md) · [`ai.md`](documentation/ai.md)

| Capability | Tier B |
|------------|--------|
| Multi-tenant JWT + RBAC in API **and** vector search | ✅ |
| Notes, files, workers, automation | ✅ |
| RAG + SSE + threads + LangGraph agent | ✅ |
| Observability + evals + CI/CD | ✅ (ship-plan gates) |

Pricing: **$5,000–8,000** MVP → **$12,000–18,000** full product (see Phase 1/2 gates).  
Profile rate **$55–70/hr** (accept **$45–55** early).

---

### Lite template — one-time build (parallel to ship-plan)

**Not a substitute for DashNote** — do this once in **2–3 evenings** so Lite jobs don’t steal Phase 1 focus.

| Step | Task | Time |
|------|------|------|
| L1 | Scaffold `templates/lite-gpt-rag` Next.js 14 App Router | 2 hr |
| L2 | `/api/upload` — pdf txt parse, chunk, Qdrant upsert | 3 hr |
| L3 | `/api/chat` — retrieve top-5, stream SSE, cite sources | 3 hr |
| L4 | Minimal chat UI (Tailwind), file list, markdown answers | 3 hr |
| L5 | Deploy demo to Vercel + `scripts/smoke.mjs` | 1 hr |
| L6 | `templates/lite-gpt-rag/README.md` — client handoff template | 1 hr |

- [ ] **Gate:** Public Lite demo URL in Upwork portfolio **separate from** DashNote
- [ ] **Gate:** Clone → rebrand → new client live in **<1 day** config changes

---

### Upgrade path (Lite → Full)

| Client ask | Action |
|------------|--------|
| “We need user accounts” | Quote Tier B auth module or Supabase Auth + migrate vectors |
| “Private docs per team” | Quote RBAC + DashNote `build_rbac_filter` pattern |
| “Agent that creates tasks/notes” | Quote agent slice + fixed scope |
| “SLA / monitoring” | Quote 7P deploy + Langfuse + monthly retainer **$500–1,500/mo** |

Document upgrades in proposal as **Phase 2** — never free scope creep.

---

## What “top 10%” and “top 3–5%” mean (concrete gates)

### Top ~10% gate (Day 14 — all must pass)

- [ ] **Live URL** — `https://app.<domain>` (frontend) + `https://api.<domain>` (API) with TLS
- [ ] **Vertical demo** — register → create note → upload file → RAG chat with citations → agent creates/updates note (record 3-min Loom/GIF)
- [ ] **CI green on PR** — `pytest` + Docker build; no secrets required
- [ ] **CD to VPS** — merge to `main` deploys; smoke script passes post-deploy
- [ ] **Golden eval set** — ≥10 cases in repo; script outputs pass/fail summary
- [ ] **Cost visible** — Langfuse and/or Grafana shows cost per RAG + agent request (document baseline in README)
- [ ] **README** — pitch, screenshots, live links, architecture one-liner, eval + cost summary

### Top ~3–5% gate (Day 45 — all must pass)

- [ ] Everything in top 10% gate, plus:
- [ ] **Evals in CI** — golden set runs on PR (mocked LLM or recorded fixtures); failing eval blocks merge
- [ ] **Retrieval metrics** — MRR or recall@k on golden set; tenant-isolation cases (member cannot retrieve private note of peer)
- [ ] **Agent evals** — ≥5 tool-use scenarios with expected tool + side-effect checks
- [ ] **Prompt/version registry** — prompts in repo with version id; traces tag `prompt_version`
- [ ] **SLO doc** — p95 latency + cost/request targets; 2-week Grafana/Langfuse screenshot trend
- [ ] **Runbook** — incident playbook (`docs/deployment/runbook.md`): rollback, migrate, LLM outage, Qdrant down
- [ ] **Security pass** — CORS locked, rate limits verified in prod, no secrets in git, dependency scan in CI
- [ ] **Public narrative** — blog post, dev.to, or LinkedIn thread: architecture + one failure you fixed (shows judgment)

---

## Phase 1 — Days 1–14 (Top ~10%)

### Week 1 — Platform, CI, backend hardening

**Theme:** Ship infra before UI polish. Follow **7P** steps in [`production.md`](documentation/production.md).

#### Day 1 — Env contract + prod compose skeleton

- [ ] **7P.1** Sync `.env.example` ↔ `src/config.py` (every `Settings` field documented)
- [ ] Create `.env.production.example` from production topology table (Supabase, Upstash, Redis Cloud, Qdrant Cloud, R2)
- [ ] Append dependency tier table to [`system.md`](documentation/system.md) (hard vs soft vs optional)
- [ ] **Gate:** `docker compose up` still works unchanged locally

#### Day 2 — Production compose + storage

- [ ] **7P.2** Create `docker-compose.prod.yml` (api, worker, migrate, Caddy/TLS — **no** db/redis/qdrant containers)
- [ ] **7P.4** Document R2 storage contract; verify worker can download uploaded files without shared volume
- [ ] Provision hosted services (or staging equivalents): Postgres, Redis×2, Qdrant Cloud, R2 bucket
- [ ] **Gate:** `docker compose -f docker-compose.prod.yml config` validates; migrate runs against hosted Postgres

#### Day 3 — Deploy scripts + smoke

- [ ] **7P.5** Add `scripts/deploy/` — `migrate.sh`, `up.sh`, `health-check.sh` (or `.ps1` + bash for VPS)
- [ ] **7P.6** Add `scripts/smoke_prod.py` — health, auth register/login, create note, optional `/ai/test-search`
- [ ] Extend [`e2e_agent_test.py`](../scripts/e2e_agent_test.py) to accept `BASE_URL` env for prod
- [ ] **Gate:** Manual deploy to Oracle VPS succeeds; smoke exits 0

#### Day 4 — CI (PR)

- [ ] **7P.7** `.github/workflows/ci.yml`:
  - Trigger: PR + push to `main`
  - Jobs: `pytest -q`, `docker build` (api image)
  - Cache pip; no production secrets
- [ ] Fix any flaky tests; ensure Windows/Linux parity (libmagic stub in conftest already exists)
- [ ] **Gate:** CI green on a test PR

#### Day 5 — CD (VPS)

- [ ] **7P.8** `.github/workflows/deploy.yml`:
  - Trigger: push to `main` (or `release/*`)
  - Build → push image (GHCR or Docker Hub)
  - SSH VPS → pull → migrate → rolling api → worker → `smoke_prod.py`
  - Secrets: `VPS_SSH_KEY`, hosted URLs in VPS `.env` only
- [ ] Cloudflare DNS + Caddy TLS for `api.<domain>`
- [ ] **Gate:** One full CD cycle from empty merge → live API health 200

#### Day 6 — AI test gap closure (minimum viable)

Add tests that prove tenant safety and AI contracts (mock LLM/Qdrant where needed):

- [ ] `tests/ai/test_rag_service.py` — citation grounding (only retrieved chunk ids); mock search
- [ ] `tests/ai/test_rbac_search_filter.py` — `build_rbac_filter` member vs admin cases
- [ ] `tests/ai/test_chat_routes.py` — 503 when `ai_enabled=false`; workspace_id never from body
- [ ] `tests/ai/test_threads_tenant.py` — cross-workspace thread → 404
- [ ] **Gate:** `python -m pytest tests/ai -q` ≥5 tests, all green in CI

#### Day 7 — Observability in prod

- [ ] Grafana Cloud remote_write from VPS prometheus (see [`observability.md`](observability.md))
- [ ] Langfuse receiving prod traces (`rag.answer`, agent spans)
- [ ] Add dashboard panel or doc row: **LLM cost / request** (Langfuse cost column or custom metric)
- [ ] **Gate:** One RAG + one agent request visible in Langfuse with cost; API metrics in Grafana Cloud

**Week 1 exit criteria:** Prod API live, CI/CD working, smoke green, baseline AI unit tests, traces + cost visible.

---

### Week 2 — Frontend MVP, evals, portfolio packaging

#### Day 8 — Frontend scaffold + auth

- [ ] Frontend repo or `frontend/` monorepo folder (your choice — link in root README)
- [ ] Auth flow: register, login, token storage, attach `Authorization` header
- [ ] Workspace context from JWT (`wid`, `role`)
- [ ] CORS: add prod frontend origin to `CORS_ORIGINS` in VPS `.env`
- [ ] **Gate:** Login against prod API from browser without CORS errors

#### Day 9 — Core product UI

- [ ] Notes list + create/edit (public/private toggle)
- [ ] File upload with progress + download link
- [ ] Notebooks list (if in scope for MVP — otherwise defer)
- [ ] **Gate:** Upload `.txt` → wait ~45s → tags/summary appear (or poll file metadata)

#### Day 10 — AI UI

- [ ] Chat panel: `POST /ai/chat/stream` SSE — render tokens + citations from `metadata` event
- [ ] Thread sidebar: `GET /ai/threads`, message history
- [ ] Agent mode toggle or separate view: `POST /ai/agent/stream` — show tool_start/tool_end
- [ ] **Gate:** Ask question about uploaded file content; citations link to source note/file

#### Day 11 — Frontend deploy

- [ ] Deploy frontend (Vercel / Cloudflare Pages / same VPS static)
- [ ] `https://app.<domain>` → prod API
- [ ] Error states: 503 LLM unavailable, 429 rate limit — user-visible messages
- [ ] **Gate:** Full demo flow on live URL without localhost

#### Day 12 — Golden eval set (v1)

Create `evals/` at repo root:

```
evals/
├── golden/
│   ├── retrieval.jsonl      # query, expected_note_id or expected_chunk_substring
│   ├── rag_answer.jsonl     # query, must_contain[], must_not_contain[]
│   └── tenant_isolation.jsonl  # setup notes, query as member B, expect empty/wrong tenant blocked
├── run_eval.py              # CLI: python evals/run_eval.py --base-url ... --token ...
└── README.md                # how to run locally + against prod staging
```

- [ ] Seed ≥10 cases from real notes/files in a **dedicated eval workspace**
- [ ] Retrieval checks: score > 0.4 gate, correct note in top-k
- [ ] RAG checks: answer mentions key fact; citations non-empty
- [ ] Tenant checks: member cannot retrieve admin's private note via search
- [ ] **Gate:** `python evals/run_eval.py` prints `PASS: 10/10` (or honest score + failures listed)

#### Day 13 — Cost tracking doc + baseline

- [ ] Script or Langfuse export: avg cost per `/ai/chat`, `/ai/agent` over 20 requests
- [ ] Document in `evals/README.md` or README:

  | Route | p50 latency | p95 latency | avg cost/request |
  |-------|-------------|-------------|------------------|

- [ ] Optional: Prometheus counter `dashnote_llm_cost_usd` if you want code-level tracking (else Langfuse-only is fine for Day 14)
- [ ] **Gate:** Numbers filled in (even if targets are “TBD improve in Phase 2”)

#### Day 14 — Portfolio packaging (recruiter-ready)

- [ ] Root [`readme.md`](../readme.md):
  - One-sentence pitch
  - Live links (app + api + `/docs` OpenAPI)
  - 2–3 screenshots or embedded GIF
  - Architecture diagram link → [`uml/diagrams.md`](uml/diagrams.md)
  - **Built:** table (RAG, agent, evals, prod URL)
  - **Metrics:** eval pass rate + cost/latency snapshot
  - **Stack:** FastAPI, Qdrant, LangGraph, LiteLLM, etc.
- [ ] Record **3-minute demo video** (Loom/YouTube unlisted) — link in README
- [ ] Pin GitHub repo description + topics: `rag`, `langgraph`, `fastapi`, `qdrant`, `multi-tenant`
- [ ] **Gate:** Ask someone unfamiliar to click README → live app in <2 minutes without your help

**Day 14 exit = Top ~10% portfolio** if all Week 1 + Week 2 gates pass.

---

## Phase 2 — Days 15–45 (Top ~3–5%)

> **Blueprint8 mapping:** Phase 2 = **Tier 1** (HITL, Langfuse retrieval-depth + experiments, fixture CI, agent goldens, cost/latency, failure modes) then **Tier 2** (recall@k/MRR, faithfulness nightly, EXPERIMENTS.md, optional hybrid/rerank).  
> Keep **Alive law**: VPS-hostile judges/rerankers stay local/nightly — never PR-blocking. Prefer **Langfuse-native** thickeners; RAGAS optional; DeepEval not required. See [`documentation/blueprint8.md`](documentation/blueprint8.md).

### Weeks 3–4 (Days 15–28) — Quality engineering (Tier 1 → start Tier 2)

#### HITL + Langfuse depth (Tier 1 centerpieces)

- [ ] HITL API-first on agent create/update ([`slice8_hitl.md`](documentation/blueprint/slice8_hitl.md))
- [ ] Enrich Langfuse retrieval spans with chunk/note ids + scores (not counts only)
- [ ] Langfuse dataset / experiment path documented for post-C-gate judges (does not replace `evals/` golden harness)

#### Evals v2 — regression gate

- [ ] Split eval data: `golden/` (stable) + `regression/` (bugs you fixed)
- [ ] Mock LLM mode for CI: recorded responses in `evals/fixtures/` OR `pytest` mocks for deterministic RAG output
- [ ] CI job `eval.yml`: run golden set on every PR (against docker compose stack in GitHub Actions service containers)
- [ ] **Gate:** Intentionally break retrieval filter → CI fails

#### Retrieval metrics (quantified) — Tier 2 / nightly OK

- [ ] Implement recall@k and MRR in `evals/run_eval.py`
- [ ] Target: recall@5 ≥ 0.8 on golden set ( tune chunk size, score threshold 0.4 )
- [ ] Document tuning experiments in `evals/EXPERIMENTS.md` (3+ iterations with numbers)
- [ ] Optional: faithfulness / answer-relevancy via Langfuse judges (or RAGAS nightly) — **not** PR-blocking

#### Agent evals

- [ ] `evals/golden/agent_tools.jsonl` — scenarios:
  - “Create a note titled X” → expect `create_note` tool + note in DB
  - “Search for Y” → expect `search_notes` + citation in answer
  - “Summarize workspace” → expect `summarize_workspace`
  - Plain question → **forbid** surprise `create_note`
- [ ] Mock or sandbox LLM for CI; real LLM for weekly manual run
- [ ] **Gate:** ≥5 agent scenarios automated

#### Prompt versioning

- [ ] Move prompts to `src/ai/prompts/` with `VERSION = "rag-v1.2"` constants
- [ ] Pass version to Langfuse trace metadata
- [ ] CHANGELOG entry when prompt changes; re-run evals before merge

---

### Week 5 (Days 29–35) — Production maturity

#### Runbook + ops

- [ ] `docs/deployment/runbook.md`:
  - Deploy / rollback steps
  - Migrate failure recovery
  - LLM provider outage (expect 503, user messaging)
  - Qdrant soft-down behavior
  - Redis outage (rate limit fail-open, cache miss)
- [ ] **7P.6 optional:** `GET /health/ai` — qdrant ping + `ai_enabled` status (do not fail hard tier)
- [ ] Alert rule in Grafana Cloud: API 5xx rate, worker queue depth

#### Security hardening

- [ ] CORS audit — no `*` in prod
- [ ] Rate limit verification script (login 429, global limit)
- [ ] `pip audit` or `dependabot` in CI
- [ ] Confirm JWT blacklist / refresh rotation tested
- [ ] OWASP spot-check: auth on all `/ai/*`, `/files/*`, no IDOR on thread routes

#### Load smoke (lightweight)

- [ ] `scripts/load_smoke.py` — 20 concurrent `/ai/chat` or `/health` for 60s
- [ ] Record p95 latency before/after; note VPS size limits
- [ ] Document in runbook — not full k6, but shows awareness

---

### Weeks 6–7 (Days 36–45) — Differentiation + narrative

#### Cost optimization story

- [ ] Embedding cache hit rate from Redis (`embed:v1:*`) — log or metric
- [ ] Compare cost: RAG-only vs agent for same question
- [ ] One optimization shipped (e.g. reduce `TOKEN_BUDGET`, smaller metadata model, cache hit improvement) with before/after numbers

#### Advanced features (pick **two** — depth over breadth)

- [ ] **HyDE or reranker** — document lift on recall@k
- [ ] **Hybrid search** — BM25 + vector (even minimal Postgres FTS)
- [ ] **Eval dashboard** — Grafana panel or static HTML report from `run_eval.py --json`
- [ ] **Human review queue** — UI for `[AUTOMATION_GOVERNANCE_BLOCK]` decisions (Slice 7.4 payoff)
- [ ] **File type expansion** — PDF eval cases in golden set
- [ ] **Inbound email → WhatsApp → optional agentic** — first-party `/integrations/inbound` (email dump MVP, WhatsApp link + text, agentic enrichment flag). OpenSpec: `openspec/changes/inbound-email-whatsapp`. **n8n is optional thin adapter only** (IMAP → inbound API); never store user JWTs in automation tools. **MUST NOT displace Days 1–14 top-10% gates** (live URL, CI/CD, evals v1, portfolio packaging) — schedule after Day 14 or as parallel evening work only.

#### Public narrative (required for top 3–5%)

- [ ] Publish one technical article (1,500–2,500 words):
  - Problem → architecture → RBAC in vector search → eval methodology → failure mode you hit
  - Link live demo + repo
- [ ] LinkedIn post with demo GIF — tag stack, not buzzwords
- [ ] Optional: 10-min conference-style talk outline in `docs/talk-outline.md`

#### Interview prep artifact

- [ ] `docs/interview-talk-track.md`:
  - 2-min pitch
  - 5 deep-dive bullets (tenancy, citations, agent tools, evals, cost)
  - 3 tradeoffs you’d defend (chunk size, fast RAG vs agent, score threshold 0.4)
  - 2 things you’d do differently at 10× scale

**Day 45 exit = Top ~3–5%** if Phase 2 gates pass and article is live.

---

## Daily rhythm (both phases)

| Time | Activity |
|------|----------|
| 30 min | Run smoke/evals; fix regressions first |
| 60 min | Docs/README/screenshots (parallel track — don’t defer to day 14) |
| Rest | Feature work from checklist |

**Rule:** Never merge without CI green. Never deploy without smoke green.

---

## Priority order (when time runs short)

1. Live prod API + CD + smoke (Tier B / portfolio)
2. Frontend happy path + live URL (Tier B)
3. Golden eval script (even 5 cases)
4. Langfuse cost snapshot in README
5. CI pytest
6. **Lite template demo** (Tier A — if you need Upwork income before Day 14)
7. Everything else in Phase 2 (including inbound email/WhatsApp — **after** items 1–5; never block Day 14)

---

## Anti-patterns (will **not** impress hiring managers)

- Demo only on localhost
- Evals that require manual eyeballing with no pass/fail script
- Frontend that ignores citations, threads, or error states
- Breaking `docker compose up` local dev while adding prod
- Giant README rewrite with no live link
- Claiming “production-ready” with no rollback story
- Optimizing prompts before tenant-isolation evals exist
- **Selling Tier B scope at Tier A price** (burns margin and timeline)
- **Calling Lite “enterprise multi-tenant”** (same oversell as cheap GPT wrappers)
- **Building full DashNote for a $1k chatbot job** (use Lite template instead)

---

## Suggested timeline calendar

| Days | Milestone |
|------|-----------|
| 1–7 | Prod + CI/CD + AI unit tests + observability |
| 8–11 | Frontend MVP + deploy |
| 12–14 | Evals v1 + cost doc + README + demo video |
| 15–28 | Evals in CI + retrieval/agent metrics + prompt versions |
| 29–35 | Runbook + security + load smoke |
| 36–45 | Cost story + 2 advanced features + public article |

---

## Success snapshot (fill in on Day 14 and Day 45)

### Day 14

| Metric | Target | Actual |
|--------|--------|--------|
| Live app URL | ✅ | |
| CI green | ✅ | |
| Golden eval pass rate | ≥80% (8/10) | |
| Avg RAG cost/request | documented | |
| p95 RAG latency | documented | |
| Demo video link | ✅ | |

### Day 45

| Metric | Target | Actual |
|--------|--------|--------|
| Eval CI blocks bad PR | ✅ | |
| recall@5 on golden set | ≥0.8 | |
| Agent eval scenarios | ≥5 automated | |
| Public technical article | ✅ | |
| Runbook tested rollback | ✅ | |
| 2-week cost/latency trend | screenshot in README | |

---

## After Day 45 — optional stretch

- Beta users (5–10) + feedback quotes in README
- SOC2-lite security doc for B2B freelance clients
- Open-source one reusable package (`tenant-rag`, `eval-runner`) extracted from repo
- Conference CFP submission
- Finish inbound channels if not picked as a Phase 2 advanced feature: email-in demo → WhatsApp text → agentic flag (see OpenSpec `inbound-email-whatsapp`)

---

*Update this file as you check items off. Cross-link completed work in [`production.md`](documentation/production.md) step log when platform tasks finish.*
