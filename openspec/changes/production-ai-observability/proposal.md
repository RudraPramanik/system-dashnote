## Why

RAG chat is Langfuse-traced, but the LangGraph agent planner, tool loop, and HITL path are not a first-class trace tree. Operators cannot run a production quality loop (trace → score → dataset → experiment) without either over-claiming coverage or building a second eval product. We need the client-grade split — Prometheus for health, Langfuse for traces/judges, fixture goldens for CI — without breaking chat≠agent, HITL, or the existing 20/20 harness.

## What Changes

- Generalize the observability facade (`observability.tracing`) so AI modules start parent traces and child spans without importing the Langfuse SDK. Keep `rag_trace` / `rag_span` as aliases so current RAG callers do not break.
- Emit a root `agent.turn` trace on `/ai/agent*` (including resume/reject) with children for `call_model`, tools, and HITL interrupt. Nested `RagService.answer()` from `search_notes` / `summarize_workspace` MUST attach as a child of that parent, not a disconnected sibling.
- Keep RAG `/ai/chat*` traces (`rag.answer` + retrieval depth + `empty_retrieval`) behaviorally compatible.
- Add low-cardinality Prometheus counters for known quality events (`empty_retrieval`, agent interrupt, LLM fallback). Do not export token cost or judge scores as high-cardinality Prometheus series.
- Add `POST /ai/feedback` so a JWT user can attach a thumbs / numeric score to the current turn’s Langfuse trace. Soft no-op when Langfuse is off.
- Wire one Langfuse dataset (seeded from goldens) and one sampled LLM-as-judge (faithfulness) as operator/nightly — **not** on the `/ai/chat` or `/ai/agent` hot path, **not** PR-blocking.
- Document the operator loop in observe/eval docs and record a first judge baseline in `docs/EXPERIMENTS.md`.
- **No BREAKING** HTTP contracts for existing chat, agent, HITL, search, health, or eval CLI. Fixture CI remains `evals/run_eval.py --mode fixture` without live LLM judges.

## Capabilities

### New Capabilities
- `ai-feedback`: Authenticated `POST /ai/feedback` attaches a user quality signal to the active AI turn’s Langfuse trace (soft when tracing is disabled).

### Modified Capabilities
- `observability-langfuse`: Tracing facade supports generic parent/child traces (not RAG-only names), agent turn trees, nested RAG under agent, quality scores, and optional Prometheus counters for known events; Langfuse remains a soft dependency.
- `ai-eval-harness`: Langfuse-native dataset + sampled faithfulness judge become an operator/nightly thickener. Fixture JSONL + `run_eval.py` remain the PR CI gate; live judges MUST NOT be required to green CI.

## Impact

- Code: `src/observability/tracing.py` (and exports), `src/ai/services/rag_service.py`, `src/ai/workflows/workspace_assistant.py`, `src/ai_routes/agent.py`, `src/ai/tools/note_tools.py` (context only — still no Langfuse SDK), `src/main.py` (Prometheus counters), new feedback route under `/ai`.
- APIs: existing `/ai/chat*`, `/ai/agent*` unchanged in request/response shape; new `POST /ai/feedback`.
- Eval: `evals/` fixture/live CLI unchanged as C-gate; Langfuse datasets/experiments configured as operator path; `docs/EXPERIMENTS.md` + `docs/documentation/observe.md`.
- Dependencies: existing Langfuse SDK only, still isolated in observability. No DeepEval/RAGAS. No Grafana requirement.
- Tenancy: feedback and traces continue to carry `workspace_id` from JWT context only; no workspace id from body for scoping.
- Soft vs hard: Langfuse and judges stay soft (app works without keys). Postgres/Redis `/health` and fixture evals stay hard gates.
