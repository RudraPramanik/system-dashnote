## Context

See proposal.md for why. Runtime contracts live in the new `ai-harness-degrade` delta and the `llm-resilience` unary-chat addition.

Today:
- `shared.llm.fallback.acompletion_with_fallback` raises `LLMUnavailableError` with `LLM_UNAVAILABLE_MESSAGE` when every candidate fails.
- Agent unary/stream already map that to HTTP 503 or an SSE error (`ai_routes/agent.py`, covered by `tests/ai/test_agent_retry.py`).
- Chat stream maps `LLMUnavailableError` / model-gone to an SSE error, then `[DONE]`.
- Unary `POST /ai/chat` only special-cases `ValueError` → 400; an uncaught `LLMUnavailableError` becomes a FastAPI 500.
- Mutation tools call `_ensure_checkpointer_for_mutation()` before interrupt / `NoteService` (`ai/tools/note_tools.py`). Existing HITL tests assert the probe string, not that `NoteService` was skipped.
- Budget exhaustion is already enforced in `ai/harness/budget_check.py` with refusal tests under `tests/ai/test_harness_budget_refusal.py`.

Process ownership stays on the API. The ARQ worker does not participate. No Qdrant read/write. Collections stay `notes_chunks` / `files_chunks`. No Alembic. No compose change. No cooldown setting.

## Goals / Non-Goals

**Goals:**

- Close the unary-chat provider-exhaustion gap to 503 with the shared unavailable message.
- Prove checkpointer-down create/update never reach `NoteService`, and that search is not blocked solely by a missing checkpointer.
- Treat budget exhaustion as already-specified behavior; wire it into the degrade matrix narrative and reuse existing tests.

**Non-Goals:**

- Provider cooldown (9H.5.2) or an in-process cooldown store.
- Thinning routes into a single harness control-plane module (9H.5.3).
- Changing Redis fail-open for budgets, HITL approval shape, or fallback candidate order.
- New Prometheus series, Alembic, settings append, or Langfuse imports inside `src/ai/*`.

## Decisions

### 1. Catch `LLMUnavailableError` on unary chat; leave fallback walk alone

**Choice:** In `POST /ai/chat`, catch `LLMUnavailableError` (and the same model-gone path chat stream already uses if it can raise before wrapping) and raise `HTTPException(503, detail=LLM_UNAVAILABLE_MESSAGE)`. Do not change `acompletion_with_fallback` candidate order.

**Why:** Agent unary already does this. Chat stream already emits the message. The gap is only the unary RAG route turning exhaustion into 500. Shared fallback stays the single walk.

**Alternatives:** Map all `Exception` from `rag.answer` to 503 (hides real bugs — rejected). Push HTTP mapping into `RagService` (pulls FastAPI into `src/ai/*` — rejected).

### 2. Strengthen checkpointer-down proof at the tool boundary; keep the existing probe

**Choice:** Keep `_ensure_checkpointer_for_mutation()` as the fail-closed gate. Extend tests so `create_note` / `update_note` with a failing `get_graph_checkpointer` never call `NoteService.create_note` / update. Add a search call under the same patch that is allowed to proceed (mock RagService / empty retrieval as needed).

**Why:** Behavior already matches the matrix. The blueprint gate is the missing no-commit assertion. Rewriting HITL around a new degrade facade would spill into 9H.5.3.

**Alternatives:** Simulate checkpointer-down only via graph compile without checkpointer (harder to assert NoteService — rejected for this substep). Commit-once without checkpointer (violates HITL — rejected).

### 3. Budget row is reference + existing tests, not a second limiter

**Choice:** Do not call `consume_ai_request_budget` from a new module in this change. Spec the budget degrade row as “reuse 9H.4.” Tasks run (or cite) the existing budget refusal suite.

**Why:** A parallel check would double-count or diverge envelopes. 9H.5.1’s job is to lock the matrix, not re-implement ceilings.

**Alternatives:** Re-implement refusal inside a new degrade helper (duplication — rejected). Skip budget from the capability entirely (blueprint matrix has three runtime rows — rejected).

### 4. No new harness package surface yet

**Choice:** Prefer route-local catch in `chat.py` plus tests under `tests/ai/`. Do not add `src/ai/harness/degrade.py` unless a tiny shared constant import from `shared.llm.fallback` is already enough.

**Why:** Control-plane extraction is explicitly 9H.5.3. Introducing a half-plane now creates a rename tax later.

**Alternatives:** Add `run_chat` / `run_agent` now (out of substep scope — rejected).

## Risks / Trade-offs

- [RagService wraps provider errors before they reach the route] → Inspect how `rag.answer` surfaces `LLMUnavailableError`; if it swallows into a generic Exception, unwrap or re-raise at the service boundary only for that type. Do not blanket-map every Exception to 503.
- [Empty retrieval already returns 200 with empty-retrieval copy] → That path is not provider exhaustion. Tests must stub fallback exhaustion, not an empty Qdrant hit list.
- [Search-without-checkpointer test needs LLM/retrieval mocks] → Mock at the tool’s RagService / search dependency; do not require a live key.
- [Agent stream already covers 503/SSE] → Prefer extending chat unary + checkpointer commit proof; do not duplicate every agent retry test unless a regression is found.

## Migration Plan

1. Ship the unary-chat 503 mapping and the stronger checkpointer/search tests in one API deploy. No schema, env, or compose change.
2. Clients that treated unary chat 500 on total outage as “retry as server bug” should treat 503 as retryable unavailable (same text as streams).
3. Rollback reverts the chat catch and the new tests; HITL probe and budget refusal remain as before.

No open questions.
