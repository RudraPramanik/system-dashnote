# DashNoteSystem

Multi-tenant notes backend: **FastAPI**, **PostgreSQL**, **Redis**, **Qdrant**, **ARQ worker**. AI features include embeddings, RBAC-aware semantic search, RAG chat (JSON + SSE), and a LangGraph workspace agent. Inbound channels (`/integrations`) cover email and WhatsApp — see [inbound-channels](docs/inbound-channels.md).

**Pitch:** multi-tenant RAG + LangGraph agent platform — live demo path, golden evals, production deploy scripts.

## Live links

| Surface | URL |
|---------|-----|
| API (local) | `http://127.0.0.1/health` after `docker compose up` |
| API (production) | _pending HTTPS after A7 — HTTP-on-IP first-boot is operator proof only, not a stranger TLS demo_ |
| App (sibling `dashnotes`) | local Playwright B-gate proven; production TLS _pending_ |
| Demo video | _pending Loom/YouTube link_ |

Do **not** claim production-live until `scripts/smoke_prod.py` exits 0 against the **HTTPS** API. An HTTP public-IP first-boot (no domain) is operator evidence only — not hire-ready.

## Quick start

```powershell
docker compose up -d --build
curl.exe -sS http://127.0.0.1/health
$env:SMOKE_BASE_URL="http://127.0.0.1"; python scripts/smoke_prod.py
```

Migrations run via the `migrate` service on startup. See [alembic/README](alembic/README) for manual Alembic commands.

## Stack

FastAPI · async SQLAlchemy · PostgreSQL · Redis/ARQ · Qdrant · LiteLLM · LangGraph · Langfuse (via `observability.tracing`) · Nginx · Docker Compose / VPS CD

## Built capabilities

| Area | Status |
|------|--------|
| RBAC-aware vector search | Yes — JWT `wid` + role filters |
| RAG chat + SSE citations | `/ai/chat`, `/ai/chat/stream` |
| LangGraph workspace agent | `/ai/agent`, `/ai/agent/stream` |
| AI feedback (optional) | `POST /ai/feedback` — JWT `wid`; thumbs or 1–5; not required to complete a turn |
| Workers / file automation | ARQ ingestion + governance |
| Inbound integrations | `/integrations` — email API key + WhatsApp webhook/link |
| Eval harness (C-gate) | `evals/run_eval.py` fixture + live |
| Thin CI | `.github/workflows/ci.yml` (pytest + docker build; no live LLM keys) |

## Quality / cost signals

| Metric | Value | Notes |
|--------|-------|-------|
| Eval pass rate (fixture) | **PASS: 20/20** | retrieval+tenant (15) + trajectory (5); CI gated |
| Eval pass rate (live local) | **PASS: 8/8** runnable live cases | seeded retrieval + forged-workspace probe; tenant dual-token cases skipped without `--token-b` |
| Cost / latency | **local/sample (2026-09-13)** — empty-retrieval gen **0 tokens** (vs up to `LLM_MAX_TOKENS=2048`); embed cache hit **0** provider calls; structured caps tags **256** / metadata **512**; chat context budget **8000** chars | Offline architecture sample via `scripts/sample_cost_latency.py` (Compose was down). Re-run with `SAMPLE_TOKEN` + Langfuse for `$` / `latency_ms`. **Not** a production SLO. |
| Optimization note | Empty-retrieval skip + embed cache (see [EXPERIMENTS EXP-002](docs/EXPERIMENTS.md)) | Before: empty chats still billed a full completion; identical chunks re-embedded. After: 0 gen tokens on empty; 0 embed provider calls on cache hit. |
| Demo video | _pending_ | |

Evidence pack: [EXPERIMENTS](docs/EXPERIMENTS.md) · [Eval harness](evals/README.md) · [Interview talk track](docs/interview-talk-track.md) (Eval Paradox) · [Messy-data pipeline](docs/documentation/ai.md#messy-data-pipeline) · [**Interview evidence guide**](docs/documentation/interview-evidence-guide.md)

## Documentation

- [Blueprint 8 ship path](docs/documentation/blueprint8.md) — Alive + Tier 0/1/2
- [Job-search gate tracker](docs/documentation/blueprint/goal.md)
- [System workflow & routing](docs/documentation/system.md)
- [AI architecture](docs/documentation/ai.md)
- [Low-level design (LLD)](docs/documentation/lld.md)
- [Auth / JWT](docs/documentation/auth.md)
- [Observability](docs/documentation/observe.md)
- [EXPERIMENTS (measure→improve)](docs/EXPERIMENTS.md)
- [Frontend guide (sibling FE)](docs/documentation/frontendguide.md)
- [Inbound channels](docs/inbound-channels.md)
- [Eval harness](evals/README.md)
- [Interview talk track](docs/interview-talk-track.md)
- [UML diagrams](docs/uml/diagrams.md)
- [Deploy runbook](docs/deployment/runbook.md)

## Architecture (chat ≠ agent)

```
Browser (dashnotes) ──► Nginx ──► FastAPI
                           │
              /ai/chat*  (fast RAG + SSE)
              /ai/agent* (LangGraph tools)
                           │
                    Worker (ARQ) ──► Qdrant / storage
```

## GitHub topics (set on the remote)

`rag` · `langgraph` · `fastapi` · `qdrant` · `multi-tenant` · `llm`
