## Context

See `proposal.md` for why. Today `observability.tracing` wraps Langfuse with `rag_trace` / `rag_span` / `score_trace`; only `RagService.answer()` and `stream_answer()` use it. LangGraph `call_model` talks to LiteLLM with no parent observation. Agent search/summarize tools call `RagService.answer()`, which opens a **sibling** `rag.answer` root. Prometheus FastAPI instrumentator already exposes `dashnote_api_*` HTTP metrics; Grafana is not in default Compose. Fixture `evals/run_eval.py --mode fixture` is the PR CI eval gate. Import law: Langfuse SDK stays in `observability.langfuse_client` / `tracing` only.

Compatibility constraint (user-mandated): `/ai/chat*` and `/ai/agent*` (including HITL resume/reject and SSE event names) keep current request/response meaning. Fixture goldens stay green without live judges.

## Goals / Non-Goals

**Goals:**
- One vendor-agnostic tracing facade with contextvar parent so nested RAG attaches under `agent.turn`.
- Agent HTTP surfaces emit `agent.turn` trees; RAG chat remains a `rag.answer` root when no agent parent is active.
- Low-cardinality Prometheus counters for empty retrieval, HITL interrupt, LLM fallback.
- Additive `POST /ai/feedback` + optional `trace_id` on AI responses for score correlation.
- Operator/nightly Langfuse dataset + sampled faithfulness judge; document it; do not put it on the request path or in PR CI.

**Non-Goals:**
- Replacing fixture CI with LLM-as-judge; RAGAS; DeepEval; Grafana as a required local service.
- Tracing embeddings, worker indexing, auto-title, inbound enrich, or `/ai/test-search` in this change.
- A quality dashboard or eval-runner HTTP API.
- Changing chat vs agent product split, HITL payload fields, or tenant/JWT scoping.
- Alembic / new DB tables (prefer optional response field + Langfuse scores).

## Decisions

### 1. Generalize facade in `observability.tracing`, keep aliases

Add `start_trace` / `span` (or keep the existing async context managers under generic names) plus a contextvar for the current parent handle. `rag_trace` / `rag_span` remain exported aliases that set name `rag.answer` when used as today.

**Why:** Callers in `RagService` keep compiling; agent code can open `agent.turn` without a second SDK wrapper.

**Alternative considered:** Langfuse LangGraph / OpenTelemetry callback imported in `workspace_assistant.py`. Rejected — violates “no Langfuse SDK in `src/ai/*`” and is harder to no-op.

**Alternative considered:** New `observability.agent_tracing` module. Rejected — two facades would drift.

### 2. Parent via contextvars, not tool-level Langfuse

When `start_trace` runs, push the handle. If `start_trace` is entered while a parent exists, start a **child** observation instead of a new root. `RagService` keeps calling `rag_trace`; under an agent turn that becomes nested `rag.answer`. Direct chat has no parent → root as today.

**Why:** `search_notes` already calls `RagService.answer()`; no tool rewrite beyond ensuring the agent route has entered the parent before graph invoke (and `contextvars` copy across asyncio tasks used by the graph).

**Alternative considered:** Pass `trace` through every tool argument. Rejected — pollutes LLM-facing tool schemas.

### 3. Where to wrap the agent

Enter `agent.turn` in `ai_routes/agent.py` around invoke / stream / resume / reject (JWT primitives already frozen there). Inside `call_model`, open a generation span via the facade. Wrap mutation tools and HITL interrupt with named spans in the tool functions or a thin ToolNode wrapper that still only imports `observability.tracing`.

**Why:** Routes own the HTTP/HITL contract (must not change). The graph owns planner/tool timing.

**Alternative considered:** Only wrap at the route and skip `call_model` spans. Rejected — operators would still not see planner tokens.

### 4. Additive `trace_id`, not a new table

When Langfuse is enabled, chat and agent JSON (and SSE `done` payload if one exists) MAY include optional `trace_id`. `POST /ai/feedback` requires JWT + `thread_id` + thumbs or 1–5; prefers `trace_id` in the body when provided; otherwise scores the latest observation for that `thread_id` in the JWT workspace via the facade. Thread must belong to `wid`. No workspace id from body for authz.

**Why:** Avoids migration; old clients ignore unknown fields; feedback is unused by existing clients so chat/agent cannot break.

**Alternative considered:** Persist last trace id on `ai_memory` threads (Alembic). Deferred unless lookup-by-thread is unreliable.

### 5. Prometheus counters in observability, not Langfuse export

`prometheus_client` Counters with **no** user/workspace/question labels: `dashnote_ai_empty_retrieval_total`, `dashnote_ai_agent_interrupt_total`, `dashnote_ai_llm_fallback_total`. Increment from the same code paths that call `score_trace` / HITL interrupt / fallback. Register/expose with the existing `/metrics` app (instrumentator already on FastAPI).

**Why:** Health and rare quality *events* belong in Prom; cost and faithfulness belong in Langfuse.

**Alternative considered:** Recording rules that scrape Langfuse. Rejected — extra moving part; Cloud already has usage dashboards.

### 6. Faithfulness judge is Langfuse-native, sampled, off hot path

Document and configure one LLM-as-judge (faithfulness vs retrieved context) on a dataset seeded from retrieval goldens / failing traces. Sampling (e.g. 5–10% or nightly batch) runs in Langfuse or a small operator script under `evals/` that is **not** invoked from `.github/workflows/ci.yml`. Chat/agent MUST NOT await a judge.

**Why:** Matches locked blueprint8 thickener; keeps CI deterministic and cheap.

**Alternative considered:** Judge inside `RagService` after generation. Rejected — latency/cost on every user request.

### 7. Compatibility gate before merge

Apply MUST keep: fixture `PASS: 20/20` (or current X/Y if goldens unchanged), existing agent HITL tests, chat response fields required today, `/health` + `/metrics` HTTP series. New tests cover facade no-op, nested parent behavior (unit with fake client), feedback 403/404 on foreign thread, and counters increment. No change to Nginx routes except exposing `/ai/feedback` through the existing `/ai` prefix.

## Risks / Trade-offs

- [Contextvar lost across graph threads] → Mitigation: set parent in the same task that runs `call_model` and tools; verify copy_context for any `run_in_executor`; test nested name under agent.
- [Optional `trace_id` surprises strict clients] → Mitigation: field optional; OpenAPI additive; existing required fields unchanged.
- [SDK v4 child observations flatten oddly in list APIs] → Mitigation: assert parent/child ids in unit tests; operator verify in Langfuse UI tree, not only list API.
- [Judge quality ≠ golden harness] → Mitigation: EXPERIMENTS labels environment; CI stays fixture; do not call judge scores production SLOs.
- [NIM cost still null in Langfuse] → Mitigation: keep ingesting token usage on generations; custom model price is operator Langfuse settings, not this change.
- [Feedback without FE] → Mitigation: curl-able contract; FE can adopt later; chat does not require it.

## Migration Plan

1. Ship facade aliases + counters behind existing env (`LANGFUSE_*` still optional).
2. Deploy API; old clients keep working (no required new fields).
3. Enable Langfuse keys as today; confirm `rag.answer` still appears, then `agent.turn`.
4. Configure dataset/judge in Langfuse Cloud (operator); do not add CI secrets.
5. Rollback: revert the release; tracing no-op if keys removed; HTTP contracts remain.

## Open Questions

None that block specs or tasks. Sampling rate (5% vs nightly-only) can be set in Langfuse UI without a spec change.
