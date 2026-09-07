# DashNoteSystem

Multi-tenant notes backend: **FastAPI**, **PostgreSQL**, **Redis**, **Qdrant**, **ARQ worker**. AI features include embeddings, RBAC-aware semantic search, RAG chat (JSON + SSE), and a LangGraph workspace agent.

**Pitch:** Hire-ready multi-tenant RAG + LangGraph agent platform — live demo path, golden evals, production deploy scripts.

## Live links

| Surface | URL |
|---------|-----|
| API (local) | `http://127.0.0.1/health` after `docker compose up` |
| API (production) | _pending — record HTTPS URL after A-gate smoke_ |
| App (sibling `dashnotes`) | local Playwright B-gate proven; production TLS _pending_ |
| Demo video | _pending Loom/YouTube link_ |

Do **not** claim production-live until `scripts/smoke_prod.py` exits 0 against the HTTPS API.

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
| Workers / file automation | ARQ ingestion + governance |
| Eval harness (C-gate) | `evals/run_eval.py` fixture + live |
| Thin CI | `.github/workflows/ci.yml` (pytest + docker build; no live LLM keys) |

## Quality / cost signals

| Metric | Value | Notes |
|--------|-------|-------|
| Eval pass rate (fixture) | **PASS: 20/20** | retrieval+tenant (15) + trajectory (5); CI gated |
| Eval pass rate (live local) | **PASS: 8/8** runnable live cases | seeded retrieval + forged-workspace probe; tenant dual-token cases skipped without `--token-b` |
| Cost / latency | **local/sample — pending fill** | Label as local until A-gate; fill from Langfuse export or fixed sample — **not** a production SLO |
| Demo video | _pending_ | |

## Documentation

- [Blueprint 8 ship path](docs/documentation/blueprint8.md) — Alive + Tier 0/1/2
- [Job-search gate tracker](docs/documentation/blueprint/goal.md)
- [System workflow & routing](docs/documentation/system.md)
- [AI architecture](docs/documentation/ai.md)
- [Frontend guide (sibling FE)](docs/documentation/frontendguide.md)
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
