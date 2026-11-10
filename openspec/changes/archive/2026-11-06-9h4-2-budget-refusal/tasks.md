## 1. Budget check (API library)

- [x] 1.1 Add `src/ai/harness/budget_check.py` with `consume_ai_request_budget(redis, user_id, workspace_id)` and `BudgetDenied`. Use `budget_keys` plus `AI_USER_REQUESTS_PER_MINUTE` and `AI_WORKSPACE_REQUESTS_PER_DAY`. Do not import `core` or FastAPI. Leave `src/ai/harness/budget.py` stdlib-only and do not export the checker from `src/ai/harness/__init__.py`
- [x] 1.2 On a present Redis client, `INCR` the user-minute and workspace-day keys, set TTLs of 120 seconds and 48 hours on first insert, and return `denied` when either count is above its ceiling. Do not write `ai_tok`. Leave `HarnessContext.remaining_budget` unset
- [x] 1.3 If either id is blank, return `denied` and do not `INCR`. If Redis is `None` or a `RedisError` is raised, log a warning and return `fail_open`. Do not catch a bare `Exception`

## 2. Chat routes (API)

- [x] 2.1 In `POST /ai/chat` and `POST /ai/chat/stream`, call the checker once with `get_redis_connection()` before `RagService`. On `denied`, return HTTP 429 with `Retry-After` when known, or an SSE `type: error` object with `code: budget_exceeded` and retry guidance, then end. Do not call the model
- [x] 2.2 When both ceilings are over, `Retry-After` is the larger positive TTL. When TTL is missing, omit the header and use `AI request limit reached. Retry shortly.` Never map this denial to HTTP 500

## 3. Agent model node (API)

- [x] 3.1 Set `budget_redis_var` from the request Redis in `agent_chat`, `agent_chat_stream`, and `agent_resume`, and reset it in `finally`. Do not set it on `agent_reject`, and do not call the checker a second time in those handlers
- [x] 3.2 In `call_model`, call the checker once before `acompletion_with_fallback`. On `denied`, raise `BudgetDenied` and do not call the provider. On `allowed` or `fail_open`, call the provider as today
- [x] 3.3 Catch `BudgetDenied` in the JSON agent handlers as HTTP 429, and in the stream generator as the same SSE error then close, including one `__cause__` if the graph wraps it. Do not let it hit the generic stream error text. Do not return `budget_exceeded` from `note_tools` or `tool_error()`

## 4. Worker and other surfaces stay put

- [x] 4.1 Do not call the checker from the ARQ worker, thread routes, feedback, `/health`, or `/health/ai`. Do not edit Alembic, `docker-compose.yml`, Qdrant (`notes_chunks` / `files_chunks`), or the global limiter
- [x] 4.2 Do not increment token usage, add a Prometheus budget series, or implement 9H.4.3, 9H.5, or 9H.6

## 5. Proof

- [x] 5.1 Add `tests/ai/test_harness_budget_refusal.py`. With a stub Redis whose counts are already over a tiny ceiling, `POST /ai/chat` is HTTP 429 and the model client is not called. A stream path emits `code: budget_exceeded` and then ends, and the model client is not called
- [x] 5.2 Assert one allowed completion increments only the user-minute and workspace-day keys, a blank id denies with no `anonymous` key, a `RedisError` fail-opens with a warning, and `call_model` raises `BudgetDenied` without calling `acompletion_with_fallback`. Assert `/ai/agent/reject` does not consume a request
- [x] 5.3 Run `python -m pytest tests/ai/test_harness_budget_refusal.py tests/ai/test_harness_budget.py tests/ai/test_harness_policy.py -q` with no live LLM key. Do not weaken the 9H.4.1 key tests or return `budget_exceeded` from note tools to go green
