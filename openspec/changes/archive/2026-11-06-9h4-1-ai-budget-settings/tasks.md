## 1. Settings (9H.4.1)

- [x] 1.1 Append `AI_USER_REQUESTS_PER_MINUTE: int = 20`, `AI_WORKSPACE_REQUESTS_PER_DAY: int = 200`, and `AI_TOKEN_BUDGET_PER_DAY: int = 0` on `Settings` in `src/config.py`, next to the existing AI agent settings. Comment that these are defaults, not a production quota, that zero tokens means the token ceiling is not configured, and that this change does not enforce them
- [x] 1.2 Name all three variables under Cost Controls in `.env.example`, with the same defaults and the same comment. Do not add a validator that rejects a user-minute at or above 100

## 2. Key text (API library, no Redis)

- [x] 2.1 Add `src/ai/harness/budget.py` using the stdlib only. Do not import `config`, FastAPI, `core`, or Redis. Do not export the helpers from `src/ai/harness/__init__.py`
- [x] 2.2 Add `budget_keys(user_id, workspace_id, when)` with no role argument and no second identity argument. Require an aware datetime, convert it to UTC, and reject a naive datetime. Return `(user_minute, workspace_day, token)` where the strings are `ai_req:{user_id}:{epoch_minute}`, `ai_day:{workspace_id}:{YYYYMMDD}`, and `ai_tok:{workspace_id}:{YYYYMMDD}`, `epoch_minute` is `floor(unix_seconds / 60)`, and the date is the UTC calendar day
- [x] 2.3 Strip each id. If the user id is blank, `user_minute` is `None`. If the workspace id is blank, `workspace_day` and `token` are `None`. Do not substitute `anonymous`, an empty segment, or the client IP

## 3. Worker, routes, and stores stay put

- [x] 3.1 Do not call the helpers from the ARQ worker, `ai_routes/chat.py`, `ai_routes/agent.py`, or the LangGraph tool node. Do not edit `src/core/security/rate_limit.py`, `HarnessContext.remaining_budget`, `tool_error()`, Alembic, `docker-compose.yml`, or Qdrant (`notes_chunks` / `files_chunks`)
- [x] 3.2 Do not increment a counter, open Redis, return `budget_exceeded`, or add HTTP 429 / SSE handling. Leave 9H.4.2 and 9H.4.3 unimplemented

## 4. Proof

- [x] 4.1 Add `tests/ai/test_harness_budget.py`. With no budget environment overrides, assert the three defaults are 20, 200, and 0, and that 20 is strictly below 100. With environment overrides, assert each setting loads that value. Assert `.env.example` names all three variables and the global limiter in `src/core/security/rate_limit.py` is still 100 per minute
- [x] 4.2 In that module, build keys for two user/workspace pairs at one fixed UTC instant and assert the shapes differ, share the UTC epoch minute and `YYYYMMDD` date, and contain no role. Use an instant whose UTC date is already the next day in a timezone behind UTC, and assert the day bucket is the UTC date
- [x] 4.3 Assert a blank user id yields `None` for the user-minute key only, a blank workspace id yields `None` for the day and token keys, and neither result contains `anonymous`. Assert a naive datetime is rejected and `HarnessContext.remaining_budget` stays unset
- [x] 4.4 Run `python -m pytest tests/ai/test_harness_budget.py tests/ai/test_harness_policy.py tests/ai/test_harness_trust.py -q` with no live LLM key. Do not add a route-level budget denial in order to go green
