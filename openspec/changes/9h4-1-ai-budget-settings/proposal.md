## Why

9H.1 through 9H.3 bind tenant, enforce note roles, and treat retrieved text as data, but AI spend is still only the global 100-requests-per-minute limiter in `src/core/security/rate_limit.py`. Blueprint 9’s next locked substep is **9H.4.1** (`docs/documentation/blueprint/slice9_cost.md`, indexed by `slice9_H.md`): name stricter per-user and per-workspace ceilings and the Redis key shapes that later substages will increment. There is no counter to refuse yet, and `budget_exceeded` stays reserved.

## What Changes

- **9H.4.1** — Append settings `AI_USER_REQUESTS_PER_MINUTE`, `AI_WORKSPACE_REQUESTS_PER_DAY`, and `AI_TOKEN_BUDGET_PER_DAY` on `Settings` and `.env.example`. The user-per-minute default is an integer below the global 100/minute cap. The three numbers are defaults, not a frozen production law.
- Add pure key builders for `ai_req:{user_id}:{minute_bucket}`, `ai_day:{workspace_id}:{utc_day}`, and `ai_tok:{workspace_id}:{utc_day}`. Identity is the JWT `user_id` and `workspace_id`. A missing id does not produce a shared anonymous key.
- Leave `HarnessContext.remaining_budget` unused. Redis key names are the future store. This change does not connect to Redis.
- **Out of scope:** incrementing counters, HTTP 429, SSE `budget_exceeded`, mid-turn tool envelopes, token increments, Redis fail-open, Prometheus outcomes, health-route tests, 9H.5 cooldown, 9H.6’s grade claim, collapsing `/ai/chat*` into `/ai/agent*`, a second permission engine, Alembic, compose changes, Qdrant writes, Slice 8, Slice 9.

## Capabilities

### New Capabilities

- `ai-harness-budget`: Configurable AI budget settings and trusted key shapes for a later per-user minute ceiling, per-workspace UTC day ceiling, and optional token ceiling. No enforcement in this change.

### Modified Capabilities

None. `ai-harness-policy` still reserves `budget_exceeded` and still does not enforce a Redis budget. `ai-harness-trust` still leaves `remaining_budget` as an unused placeholder.

## Impact

- Code: append-only fields on `src/config.py` and names in `.env.example`. New pure helpers under `src/ai/harness/` (import law: `config`, `ai.*`, stdlib). No router, graph, worker, or `RateLimiter` edit.
- APIs: `/ai/chat*` and `/ai/agent*` both stay mounted and keep their current success and error behavior. No new HTTP status, SSE event, or tool-return code is produced by this change. Threads, feedback, and `/ai/agent/reject` are untouched.
- Tenancy: key identity is the server-side user and workspace. Role rules do not change. Model-supplied ids are not an input to the builders.
- Dependencies: Redis stays a hard dependency of `/health` and a soft, unused dependency of these settings. This slice does not read or write Redis, so a Redis outage does not change AI availability. Postgres and Qdrant are unchanged (`notes_chunks` / `files_chunks`). No Alembic migration.
- Tests: settings load, the user-minute default is `< 100`, and key strings match the three shapes, including refusal to mint an anonymous key. No live LLM key.
- Blueprint map: **9H.4.1 only**. 9H.4.2 will consume these keys for 429 and SSE refusal. 9H.4.3 will add Redis fail-open and the outcome metric.
