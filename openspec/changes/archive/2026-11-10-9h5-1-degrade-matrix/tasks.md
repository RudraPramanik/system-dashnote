## 1. Unary chat provider exhaustion (API)

- [x] 1.1 In `POST /ai/chat` (`src/ai_routes/chat.py`), catch `LLMUnavailableError` from `rag.answer` and raise HTTP 503 with `LLM_UNAVAILABLE_MESSAGE`. Do not blanket-map other exceptions to 503. Keep the existing `ValueError` → 400 path
- [x] 1.2 Confirm chat stream already emits SSE `type: error` with that message on `LLMUnavailableError`; only adjust if it currently drops to a silent empty success. Do not change `acompletion_with_fallback` candidate order

## 2. Checkpointer-down fail-closed proof (API tools)

- [x] 2.1 Keep `_ensure_checkpointer_for_mutation()` as the gate in `create_note` / `update_note`. Do not add a commit path that skips the probe. Do not implement provider cooldown or a harness control-plane module
- [x] 2.2 Confirm `search_notes` / summarize do not call the checkpointer probe; no code change if already true

## 3. Worker and other surfaces stay put

- [x] 3.1 Do not call new degrade logic from the ARQ worker, thread routes, feedback, `/health`, or `/health/ai`. Do not edit Alembic, `docker-compose.yml`, Qdrant (`notes_chunks` / `files_chunks`), budget Redis keys, or the global limiter
- [x] 3.2 Do not implement 9H.5.2 cooldown, 9H.5.3 control plane, or 9H.6 grade claims. Do not collapse `/ai/chat*` into `/ai/agent*`

## 4. Proof

- [x] 4.1 Add `tests/ai/test_harness_degrade.py` (or extend the closest existing AI route test module). Stub `rag.answer` (or the completion path) to raise `LLMUnavailableError` and assert `POST /ai/chat` returns HTTP 503 whose detail includes `LLM temporarily unavailable; retry shortly`, with no empty successful answer body
- [x] 4.2 With `get_graph_checkpointer` failing, invoke `create_note` and `update_note` and assert `NoteService.create_note` / update are never called and the tool result identifies checkpointer / mutation unavailability. Under the same patch, invoke `search_notes` and assert it is not blocked solely by the missing checkpointer (mock retrieval as needed)
- [x] 4.3 Reuse existing budget refusal coverage: run `tests/ai/test_harness_budget_refusal.py` (or a thin assert that over-budget still yields 429 / SSE `budget_exceeded` without a provider call). Do not duplicate the limiter
- [x] 4.4 Run `python -m pytest tests/ai/test_harness_degrade.py tests/ai/test_harness_budget_refusal.py tests/ai/test_agent_hitl.py tests/ai/test_agent_retry.py -q` with no live LLM key. Do not skip degrade assertions to go green
