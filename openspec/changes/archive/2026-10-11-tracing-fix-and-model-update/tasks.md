## 1. Langfuse client labels

- [x] 1.1 Add optional `LANGFUSE_TRACING_ENVIRONMENT` and an effective value (`production` when debug is off, `development` when debug is on, explicit override wins). Document the name in `.env.example` and `.env.production.example` with an empty or commented example, no live keys.
- [x] 1.2 Pass that environment into the Langfuse client at init, and set `OTEL_SERVICE_NAME=dashnote-api` before construction only when it is unset. Keep init soft-fail and do not log keys.

## 2. Named traces, child spans, and time to first token

- [x] 2.1 On root `rag.answer` and `agent.turn`, call `update_trace` with that name and end the root observation on every exit path, including errors and empty retrieval, then flush.
- [x] 2.2 Pass `as_type="span"` for `retrieval` and `context_building`, keep generation `as_type`, and still `end()` the span if output update fails.
- [x] 2.3 Add a span-handle first-token mark used by the chat and agent stream loops, and write Langfuse `completion_start_time` on generation finalize. Leave non-streaming completions unset. Do not import the Langfuse SDK from `src/ai/*`.

## 3. Soft health Langfuse flag

- [x] 3.1 Add `langfuse.enabled` and `langfuse.host` to `GET /health/ai` with no key material. Do not let that block change `GET /health` or the AI status solely because keys are missing.
- [x] 3.2 Cover enabled, disabled, and hard-health isolation in `tests/core/test_health_ai.py` (or the closest existing health test).

## 4. Tracing tests and operator notes

- [x] 4.1 Add observability tests that a fake client records `update_trace`, `as_type="span"` for retrieval and context building, `end` on the root, and a first-token timestamp on a streamed generation.
- [x] 4.2 Note in `docs/documentation/observe.md` how to filter hosted chats (`environment=production`, service `dashnote-api`, parent `rag.answer` / `agent.turn`) and that a shared project can still contain other apps.

## 5. Faster model defaults

- [x] 5.1 Set code defaults and `.env.example` / `.env.production.example` to `LLM_MODEL=gemini/gemini-2.5-flash` and `LLM_MODEL_FALLBACKS=nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b`. Remove `gpt-oss-20b` from those defaults. Do not edit filled `.env` or `.env.production`.
- [x] 5.2 Update `docs/documentation/ai.md` and `docs/nvidia.md` so the documented primary is Gemini Flash and Lightning is the fallback. Leave the L2 judge model unchanged.
- [x] 5.3 Adjust tests that assume the old default candidate list. Keep tests that intentionally pin `gpt-oss-20b` as an explicit override.

## 6. Configured versus cached model on soft health

- [x] 6.1 Extend the `llm` object on `GET /health/ai` with `configured_model` and `cached_model`, leaving existing `model` as the resolved id. `cached_model` is null when nothing is cached.
- [x] 6.2 Test the split fields, including a cached id that differs from the configured primary.
- [x] 6.3 Document the operator step: set the two model lines on the VPS `.env`, then recreate `api` and `worker` so the in-process cache clears. Do not commit that file.
