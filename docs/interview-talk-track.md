# Interview talk track — DashNoteSystem

## 2-minute pitch

I built a **multi-tenant notes backend** with RBAC-aware RAG and a LangGraph agent that can mutate notes through the service layer—not a thin ChatGPT wrapper. Retrieval always scopes by JWT workspace (`wid`) and mirrors app permissions in Qdrant. Fast RAG (`/ai/chat*`) and the agent (`/ai/agent*`) stay as separate surfaces so demos stay snappy while tool loops stay explicit. The portfolio gate is Alive: local Compose and a stranger FE demo path, plus a golden eval harness (`evals/run_eval.py`) with fixture and live modes—fixture is PR-safe; live proves against a real API. Platform work covers thin CI, prod compose, smoke, and CD to a small VPS with hosted data plane.

## Three tradeoffs (be ready to defend)

1. **Chat ≠ agent** — Keeping both routes costs UI surface area, but collapsing them would either slow every Q&A or hide tool mutations. Interviewers hear intentional product boundaries.
2. **Fixture vs live evals** — PR CI never requires paid live LLM keys. Fixture goldens gate determinism; live `--base-url` runs are operator/nightly. Honest pass rates beat flaky green CI.
3. **Hosted data plane + thin VPS** — Postgres/Redis/Qdrant/R2 stay off the 1–2GB box; the VPS runs api/worker/nginx. Ops complexity moves to managed services so demos stay deployable without melting RAM on local rerankers or Neo4j.

## Optional fourth (if asked about GraphRAG / HITL)

GraphRAG and multi-agent supervisors stay deferred. **HITL is live on the API:** agent `create_note` / `update_note` emit `approval_required` then resume/reject (`POST /ai/agent/resume|reject`). Langfuse retrieval spans log chunk/note ids + scores. Failure modes (empty retrieval, LLM 503, embed lag) are in the deploy runbook.

## Failure modes (30-second version)

1. **Empty retrieval** — honest fallback answer; check embeds / workspace / Langfuse `empty_retrieval`.
2. **LLM 503** — provider unavailable; chat and agent return safe errors; demo `/ai/chat` vs agent separately.
3. **Embed lag** — note exists in DB before Qdrant; wait for worker; don’t claim instant search.
