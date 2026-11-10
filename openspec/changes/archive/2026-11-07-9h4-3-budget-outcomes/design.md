## Context

See proposal.md for why. Requirements live in `specs/ai-harness-budget/spec.md`.

`consume_ai_request_budget` in `src/ai/harness/budget_check.py` already returns `allowed`, `denied`, or `fail_open`. Chat routes call it once before `RagService`. `call_model` calls it once before `acompletion_with_fallback`. `/health` and `/health/ai` do not call it. `src/observability/metrics.py` already holds the unlabeled AI counters (`dashnote_ai_empty_retrieval_total`, `dashnote_ai_agent_interrupt_total`, `dashnote_ai_llm_fallback_total`). `src/ai/services/rag_service.py` already imports `inc_empty_retrieval` from that module. This check runs in the API process. The ARQ worker does not call it. No Qdrant read or write. Collections stay `notes_chunks` and `files_chunks`. No Alembic migration, no settings change, and no compose change.

## Goals / Non-Goals

**Goals:**

- One increment per decision, on the same return paths the checker already has.
- A single series whose only label is the outcome.
- Health handlers stay free of the limiter, and a test shows that.

**Non-Goals:**

- A Langfuse attribute, a new span, or any import of the Langfuse SDK.
- Token-key increments, new Redis commands, or a change to 429 / SSE behavior.
- Counting from the worker, from `/ai/agent/reject`, or from thread and feedback routes.

## Decisions

### 1. Count inside the checker, once per return

**Choice:** `consume_ai_request_budget` calls `inc_ai_budget_outcome(decision.outcome)` immediately before every return, including the blank-id denial and both fail-open returns.

**Why:** Chat and the agent model node already share this function, and each completion calls it once. A route-level increment would miss resume and later tool iterations, or would double-count if both layers incremented. Health never enters the function, so those requests do not move the series.

**Alternatives:** Increment in `ai_routes` only (misses `call_model` — rejected). Increment in both the route and `call_model` (double count — rejected).

### 2. Extend the existing AI counter module

**Choice:** Add `dashnote_ai_budget_outcome_total` in `src/observability/metrics.py` with one label, `outcome`. `inc_ai_budget_outcome` accepts only `allowed`, `denied`, and `fail_open`. Any other string is ignored and does not create a label. The checker imports that function the same way `rag_service` imports `inc_empty_retrieval`. It does not import `observability.tracing` or the Langfuse SDK, and it does not import `core`.

**Why:** The series sits with the other AI counters and is already scraped at `/metrics`. A second registry inside `src/ai` would split the same scrape. The label allow-list keeps a bad string from becoming a new series.

**Alternatives:** A counter declared inside `budget_check.py` (splits the AI metrics — rejected). A context-var callback set by the routes (extra machinery for one increment — rejected). User or workspace labels (the spec forbids them — rejected).

### 3. Health proof is source inspection of the handlers

**Choice:** A unit test reads the source of the `/health` and `/health/ai` handlers and asserts they do not reference `consume_ai_request_budget`, `ai_req`, `ai_day`, or `ai_tok`. It does not call Redis.

**Why:** The blueprint allows a test or a code inspection. The handlers are not wired today. A live health call would require Postgres and Redis and would not prove the AI keys were untouched.

**Alternatives:** An integration test that scrapes Redis keys after `/health` (needs the full stack for a fact the source already shows — rejected).

## Risks / Trade-offs

- [The checker imports `observability.metrics`] → That import already exists on the RAG path. This change does not import Langfuse or `core`. The counter call does not open Redis.
- [A metric error could fail an AI call that Redis allowed] → `Counter.inc` is in-process. Do not wrap it in a bare `except`. If registration itself fails at import, the API process fails at startup the same way the other AI counters would.
- [Fail-open traffic looks like healthy traffic in a sum without the label] → Dashboards must filter on `outcome`. The warning log stays.
- [Multiple API workers each keep their own counter] → Same as the existing AI counters. Prometheus scrapes each process. Cooldown and budget Redis are unchanged.

## Migration Plan

1. Register the counter and increment it from the checker. No schema, env, or compose change.
2. After deploy, `/metrics` shows the new series at zero until the next AI completion. Old `ai_req` and `ai_day` keys are untouched.
3. Rollback removes the increment and the series registration. In-flight counts disappear with the process. Redis keys and the 429 path stay.

No open questions.
