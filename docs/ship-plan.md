# DashNote Ship Plan — Top 10% (14 days) → Top 3–5% (45 days)

**Purpose:** Actionable checklist to turn this repo from a strong backend portfolio into a hiring-manager-ready AI product. Aligns with existing platform work in [`docs/documentation/production.md`](documentation/production.md) (slice **7P**) and observability in [`docs/observability.md`](observability.md).

**Related docs:** [system](documentation/system.md) · [AI architecture](documentation/ai.md) · [LLD](documentation/lld.md) · [UML diagrams](uml/diagrams.md) · [deploy laws](documentation/deploy-low.md)

---

## Current baseline (Day 0)

| Strength | Gap |
|----------|-----|
| Multi-tenant RAG + LangGraph agent + worker automation | No live product URL |
| Langfuse traces, Prometheus, Grafana | No CI/CD (`.github/workflows/` missing) |
| Excellent internal docs + architecture laws | AI path test coverage thin |
| Docker Compose local stack | Frontend not wired to prod |
| E2E scripts (`scripts/e2e_agent_test.py`) | No eval harness or cost SLO doc |

**Target after 14 days:** Recruiter clicks live app in 30s; tech lead sees CI, prod, evals, cost — **top ~10%** of mid-level AI engineer portfolios.

**Target after 45 days:** Regression-gated quality, production ops story, differentiated depth — **top ~3–5%**.

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

### Weeks 3–4 (Days 15–28) — Quality engineering

#### Evals v2 — regression gate

- [ ] Split eval data: `golden/` (stable) + `regression/` (bugs you fixed)
- [ ] Mock LLM mode for CI: recorded responses in `evals/fixtures/` OR `pytest` mocks for deterministic RAG output
- [ ] CI job `eval.yml`: run golden set on every PR (against docker compose stack in GitHub Actions service containers)
- [ ] **Gate:** Intentionally break retrieval filter → CI fails

#### Retrieval metrics (quantified)

- [ ] Implement recall@k and MRR in `evals/run_eval.py`
- [ ] Target: recall@5 ≥ 0.8 on golden set ( tune chunk size, score threshold 0.4 )
- [ ] Document tuning experiments in `evals/EXPERIMENTS.md` (3+ iterations with numbers)

#### Agent evals

- [ ] `evals/golden/agent_tools.jsonl` — scenarios:
  - “Create a note titled X” → expect `create_note` tool + note in DB
  - “Search for Y” → expect `search_notes` + citation in answer
  - “Summarize workspace” → expect `summarize_workspace`
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

1. Live prod API + CD + smoke
2. Frontend happy path + live URL
3. Golden eval script (even 5 cases)
4. Langfuse cost snapshot in README
5. CI pytest
6. Everything else in Phase 2

---

## Anti-patterns (will **not** impress hiring managers)

- Demo only on localhost
- Evals that require manual eyeballing with no pass/fail script
- Frontend that ignores citations, threads, or error states
- Breaking `docker compose up` local dev while adding prod
- Giant README rewrite with no live link
- Claiming “production-ready” with no rollback story
- Optimizing prompts before tenant-isolation evals exist

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

---

*Update this file as you check items off. Cross-link completed work in [`production.md`](documentation/production.md) step log when platform tasks finish.*
