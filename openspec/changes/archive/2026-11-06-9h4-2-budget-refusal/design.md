## Context

See proposal.md for why. Requirements live in `specs/ai-harness-budget/spec.md`.

`budget_keys()` in `src/ai/harness/budget.py` formats `ai_req`, `ai_day`, and `ai_tok` and does not touch Redis. Settings defaults are 20 per user per minute, 200 per workspace per UTC day, and 0 for tokens. `call_model` in `src/ai/workflows/workspace_assistant.py` is the only agent completion site, including resume and later tool iterations. Chat calls `RagService.answer` / `stream_answer` from `src/ai_routes/chat.py`. `src/ai/*` may import `config` and `redis.asyncio`, and must not import `core` or FastAPI. The global limiter already fail-opens on `RedisError` and skips `/health` and `/health/ai`.

This check runs in the API process. The ARQ worker does not call it. No Qdrant read or write. Collections stay `notes_chunks` and `files_chunks`. No Alembic migration and no compose change.

## Goals / Non-Goals

**Goals:**

- One consume function at each provider completion, using the existing key formatter and the JWT ids.
- 429 or the current SSE error object when a request ceiling is over, with the provider not called.
- Redis failures allow the completion. A blank id denies it.

**Non-Goals:**

- Incrementing `ai_tok`, reading usage metadata, or enforcing `AI_TOKEN_BUDGET_PER_DAY`.
- A Prometheus series, a Langfuse attribute, or a new health assertion beyond leaving `/health` and `/health/ai` unwired. That is 9H.4.3.
- Provider cooldown, a second envelope, or `budget_exceeded` from `note_tools`.

## Decisions

### 1. Count at the completion, not twice at the route

**Choice:** Add `consume_ai_request_budget(redis, user_id, workspace_id)` in `src/ai/harness/budget_check.py`. It calls `budget_keys`, `INCR`s the user-minute and workspace-day keys, and compares them with `AI_USER_REQUESTS_PER_MINUTE` and `AI_WORKSPACE_REQUESTS_PER_DAY`. Chat routes call it once before `RagService`. `call_model` calls it once immediately before `acompletion_with_fallback`. Agent HTTP handlers do not call it again.

**Why:** Resume and mid-turn completions never return to the route. A route check plus a `call_model` check would charge the first agent completion twice.

**Alternatives:** Increment only on the HTTP handlers (misses later iterations — rejected). Peek without `INCR` in the route and `INCR` in the node (two round trips and a race — rejected).

### 2. Redis stays out of `core` by using a context var

**Choice:** Agent routes set `budget_redis_var` from `get_redis_connection()` around `agent_chat`, `agent_chat_stream`, and `agent_resume`, and reset it in `finally`, same as `harness_context_var`. `call_model` reads that var. Chat routes pass the dependency result straight into `consume_ai_request_budget`. `budget.py` stays stdlib. The new module may import `config` and `redis`.

**Why:** `call_model` cannot import `core.redis`. A Redis client on `AgentState` would be checkpointed. The context var lives for one request and is not serialized.

**Alternatives:** Open a new Redis client inside `call_model` from `REDIS_URL` (a second pool — rejected). Import `get_async_redis` from `core` (import law — rejected).

### 3. Denial, blank ids, and Redis errors are different outcomes

**Choice:** Return `allowed`, `denied`, or `fail_open`.

- `denied`: either counter is above its ceiling, or either id is blank. Do not `INCR` when an id is blank. Raise `BudgetDenied` from `call_model` before the provider call. JSON routes raise HTTP 429. Streams emit `{"type":"error","code":"budget_exceeded","message":...}` and then the existing `[DONE]` frame. Include `retry_after` on that object when known.
- `Retry-After`: minute key TTL is 120 seconds; day key TTL is 48 hours. If both ceilings are over, send the larger positive TTL, because the caller is blocked until both windows move. If TTL is missing, omit the header and use the message `AI request limit reached. Retry shortly.`
- `fail_open`: Redis is `None`, or `INCR` / `EXPIRE` / `TTL` raises `RedisError`. Log a warning and continue. Do not catch a bare `Exception`.
- Note tools and `tool_error()` stay as they are. The client-visible code is the SSE field and the 429, not a tool string the model must read.

**Why:** The blueprint’s client contract is 429 or the existing SSE error. Feeding `budget_exceeded` back into the model would require the completion this step is forbidden to start. Fail-open matches the global limiter and the architecture law, without the 9H.4.3 metric.

**Alternatives:** Fail closed on Redis errors (turns a Redis blip into an AI outage — rejected). Reuse `RateLimiter.check` (IP fallback, `rate_limit:` keys, and HTTPException inside `src/ai` — rejected).

### 4. Where the exception surfaces

**Choice:** `agent_chat` and `agent_resume` catch `BudgetDenied` and return 429. Stream generators catch it around the graph stream, including one `__cause__` if LangGraph wraps the node error, emit the SSE object, and return. They must not let that exception fall into the generic “please try again” handler. Chat stream checks before `stream_answer`, so a denial emits the error frame and the existing `finally` still writes `[DONE]` once.

**Why:** Today both stream handlers turn unknown exceptions into a generic error with no `code`. A budget denial has to stay distinct and must not be HTTP 500.

## Risks / Trade-offs

- [Defaults of 20/minute and 200/day become live] → They were documented as defaults. A demo that loops chat can now see 429. Rollback is reverting the check; keys expire on their TTL.
- [A mid-turn denial can follow tokens already streamed] → The denied completion does not call the provider and does not emit more tokens. Earlier tokens stay on the wire. The stream then sends `budget_exceeded` and closes.
- [An agent route forgets `budget_redis_var`] → `call_model` sees `None` and fail-opens, so the ceiling does not apply. Set the var on all three model entrypoints and reset it in `finally`.
- [LangGraph wraps `BudgetDenied`] → The stream and JSON handlers unwrap one cause before using the generic error path.
- [Scope creep into metrics or token totals] → Tasks stop at the request ceilings, the refusal, and the Redis fail-open warning.

## Migration Plan

1. Add the checker and wire chat plus `call_model`. No schema, compose, or env change. Existing deploys pick up the defaults already in settings.
2. First requests after deploy start at count 1. Nothing backfills old traffic.
3. Rollback removes the check. Leftover `ai_req` and `ai_day` keys expire with their TTL. No database undo.

No open questions. On archive, replace the `ai-harness-budget` purpose sentence that still says this capability does not refuse calls. The delta does not carry a purpose, because the capability already exists.
