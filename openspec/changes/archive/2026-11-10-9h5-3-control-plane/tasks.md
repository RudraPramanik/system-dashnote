## 1. Control-plane module

- [x] 1.1 Add `src/ai/harness/control_plane.py` that wraps trusted-context bind/reset (`HarnessContext` / `harness_context_var`) and, for agent paths, `budget_redis_var` set/reset. Do not import FastAPI. Do not call repositories or NoteService
- [x] 1.2 In the same module, expose a shared budget-gate helper that calls existing `consume_ai_request_budget` (and reuses `BudgetDecision` / `BudgetDenied` / `budget_error_payload` / `denial_message` / `retry_after_header` from `budget_check`). Do not invent a second Redis key scheme or weaken fail-open
- [x] 1.3 Add shared provider-unavailable helpers that reuse `LLMUnavailableError` / `LLM_UNAVAILABLE_MESSAGE` / `is_model_gone` from `shared.llm.fallback` so routes do not re-copy message strings. Do not move cooldown logic out of fallback

## 2. Thin chat routes

- [x] 2.1 In `ai_routes/chat.py`, replace direct `consume_ai_request_budget` calls on unary and stream with the control-plane budget gate. Map denied → existing 429 / SSE `budget_exceeded`. Route modules MUST NOT call `consume_ai_request_budget` directly afterward
- [x] 2.2 Map `LLMUnavailableError` (and model-gone where already handled) through the shared unavailable helpers to 503 / SSE error. Keep RagService as the answer implementation. Do not collapse chat into agent

## 3. Thin agent routes

- [x] 3.1 Replace `_bind_harness_context` and local `budget_redis_var` set/reset on `/ai/agent`, `/ai/agent/stream`, `/ai/agent/resume`, and `/ai/agent/reject` with the control-plane bind/reset helpers. Reject MUST still skip AI request budget spend
- [x] 3.2 Map `BudgetDenied` and `LLMUnavailableError` on agent unary/stream through the shared denial helpers to 429 / 503 / SSE. Keep mid-turn model-node budget checks from 9H.4.2. Keep HITL interrupt / approval SSE events unchanged
- [x] 3.3 Do not implement 9H.6 grade claims. Do not rewrite cooldown, checkpointer probe, Alembic, `docker-compose.yml`, or Qdrant (`notes_chunks` / `files_chunks`). Do not import Langfuse SDK inside `src/ai/*`

## 4. Proof

- [x] 4.1 Add or extend `tests/ai/test_harness_control_plane.py` (or equivalent): assert chat/agent route modules no longer import/call `consume_ai_request_budget` directly; over-budget still yields 429 / SSE `budget_exceeded` without a provider call; provider exhaustion still yields 503 / unavailable SSE
- [x] 4.2 Run `python -m pytest tests/ai/test_harness_control_plane.py tests/ai/test_harness_budget_refusal.py tests/ai/test_harness_degrade.py tests/ai/test_agent_retry.py -q` plus the existing chat citation / agent HITL suites that already cover those contracts. No live LLM key. Do not skip denials to go green
