## Why

9H.4.1 names AI ceilings and Redis key shapes, but nothing increments them, so chat and agent calls still spend a provider completion with only the global 100-requests-per-minute limiter in front. Blueprint 9’s next locked substep is **9H.4.2** (`docs/documentation/blueprint/slice9_cost.md`): before each chat or agent model call, enforce the user-minute and workspace-day counters and refuse with 429 or the existing SSE error shape.

## What Changes

- **9H.4.2** — Before a model completion, increment `ai_req:{user_id}:{utc_minute}` and `ai_day:{workspace_id}:{utc_day}` from the JWT identity. Over either ceiling: do not call the provider.
- **BREAKING** for those AI clients only: `POST /ai/chat` and `POST /ai/agent` return HTTP 429 with `Retry-After` when the window end is known. `POST /ai/chat/stream` and `POST /ai/agent/stream` emit the existing SSE `type: error` object plus `code: budget_exceeded`, then close. `/ai/agent/resume` is included because it continues the model loop.
- A later model call in the same agent turn (after tools) uses the same refusal. Note tools still do not invent `budget_exceeded`.
- A blank user or workspace id denies that call. It does not share an anonymous key. Redis connection failures log a warning and allow the call, so a Redis blip does not become HTTP 500. Outcome metrics and the health-route proof stay in 9H.4.3.
- **Out of scope:** token-key increments, Prometheus budget outcomes, provider cooldown, 9H.5, 9H.6’s grade claim, collapsing `/ai/chat*` into `/ai/agent*`, a second permission engine, Alembic, compose changes, Qdrant writes, Slice 8, Slice 9.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-harness-budget`: Request ceilings are now enforced before model calls. The previous requirement that this capability must not refuse chat or agent is replaced.

## Impact

- Code: a Redis check beside `src/ai/harness/budget.py` (that module stays stdlib and still does not connect). Chat routes check once before `RagService`. `call_model` in `src/ai/workflows/workspace_assistant.py` checks before `acompletion_with_fallback`, which covers `/ai/agent`, `/ai/agent/stream`, and `/ai/agent/resume` without counting the same completion twice. Agent routes bind the request Redis on a context var the way they already bind `HarnessContext`. `src/ai/*` still does not import `core`.
- APIs: `/ai/chat*` and `/ai/agent*` both stay mounted. New failure on those generation routes is 429 or SSE `budget_exceeded`. `/ai/agent/reject`, threads, and feedback do not spend a request. SSE keeps `type: error` and still ends with `[DONE]`. No new event type.
- Tenancy: counters use the server-bound user and workspace only. Role rules do not change. A missing id fails closed for that AI call.
- Dependencies: Redis is a soft dependency of this check. Errors and a missing client fail open and log a warning. `/health` and `/health/ai` stay unwired to AI budget keys, so Redis remains a hard dependency of `/health` only through the existing health checks. No Postgres or Qdrant change (`notes_chunks` / `files_chunks`). No Alembic migration.
- Tests: a tiny limit yields 429 or SSE `budget_exceeded` and the model client is not called. No live LLM key.
- Blueprint map: **9H.4.2 only**. On archive, edit the `ai-harness-budget` purpose so it no longer says this capability refuses nothing. Delta specs do not carry a new purpose for an existing capability.
