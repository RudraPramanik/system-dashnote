## Context

See proposal.md for why. Requirements live in `specs/ai-harness-budget/spec.md`.

The global limiter in `src/core/security/rate_limit.py` is a fixed window of 100 requests per minute. It raises HTTP 429, falls back to the client IP when `RequestContext` is missing, and skips `/health` and `/health/ai`. AI routes already take `user_id` and `workspace_id` from the JWT. `HarnessContext` exists only on `/ai/agent*` and carries an unused `remaining_budget`. `tool_error()` already reserves `budget_exceeded` and does not read Redis.

`src/ai/*` may import `config`, `ai.*`, `shared.*`, the stdlib, and third-party packages. It must not import `core.security` or FastAPI. Chat routes do not build a `HarnessContext`. This work adds library code in the API image. The ARQ worker must not call it. No LangGraph tool node calls it in this change. No Qdrant read or write. Collections stay `notes_chunks` and `files_chunks`. No Alembic migration. `docker-compose.yml` stays the full stack and gains no service.

## Goals / Non-Goals

**Goals:**

- Three append-only settings with defaults an operator can override.
- Pure key text for the user-minute, workspace-day, and token counters, keyed from trusted ids and a UTC timestamp.
- A missing id yields no key, so a later check cannot bill a shared anonymous bucket.

**Non-Goals:**

- Calling Redis, incrementing, or refusing a request. That is 9H.4.2 and 9H.4.3.
- Populating `HarnessContext.remaining_budget` or building `HarnessContext` on the chat path.
- Reusing `RateLimiter.check`.
- Editing routers, the graph, the worker, compose, or canonical docs.

## Decisions

### 1. Settings stay on `Settings`; key text stays stdlib

**Choice:** Append the three integers on `src/config.py` next to the existing AI agent settings. Put key builders in `src/ai/harness/budget.py` with stdlib only. Do not export them from `src/ai/harness/__init__.py`. Do not import `config` from the key module.

**Why:** Settings are append-only and already load through pydantic-settings. The graph and the routes can both import `ai.harness.budget` later without FastAPI. Keeping Redis and settings out of the key module makes the UTC tests deterministic.

**Defaults, documented as defaults in `.env.example` under Cost Controls:**

| Setting | Default | Meaning |
|---------|---------|---------|
| `AI_USER_REQUESTS_PER_MINUTE` | 20 | Below the global 100/minute cap. Not a production quota. |
| `AI_WORKSPACE_REQUESTS_PER_DAY` | 200 | Positive workspace-day ceiling. Not a production quota. |
| `AI_TOKEN_BUDGET_PER_DAY` | 0 | Zero means the token ceiling is not configured. |

**Alternatives:** A validator that rejects a user-minute at or above 100 (blocks a deliberate operator override — rejected; the spec only constrains the default). Storing the ceilings on `HarnessContext.remaining_budget` (one process-local integer cannot be the cross-process counter — rejected). Putting the builders in `core.security.rate_limit` (the agent graph cannot import `core` — rejected).

### 2. One identity pair, UTC buckets, no key when the id is blank

**Choice:** Builders take the trusted `user_id`, the trusted `workspace_id`, and an aware UTC `datetime`. They have no role argument and no second id that could override the first.

- User-minute: `ai_req:{user_id}:{epoch_minute}` where `epoch_minute` is `floor(unix_seconds / 60)`.
- Workspace-day: `ai_day:{workspace_id}:{YYYYMMDD}` in UTC.
- Token: `ai_tok:{workspace_id}:{YYYYMMDD}` with that same UTC date.
- Strip the id. If it is empty, return `None` for that key. Do not substitute `anonymous`, the client IP, or an empty segment.

**Why:** Chat and the agent already freeze those two ids from the JWT. A pure function cannot see model tool arguments unless a caller passes them, and the signature gives the caller only one slot per id. UTC avoids a laptop and the VPS flipping the day bucket at different local midnights. `None` is the “no key” result the spec requires, without an HTTP exception this package cannot raise.

**Alternatives:** Local server date (splits one workspace across two daily counters — rejected). Reusing the global limiter’s IP fallback (shared anonymous AI bucket — rejected). Raising on a blank id (turns a missing context into an exception type the routes do not catch yet — rejected for this substep).

### 3. Sync contract for 9H.4.2 and 9H.4.3 (do not implement it here)

| This change leaves | Later substep uses | Later substep must not |
|--------------------|--------------------|------------------------|
| The three settings and the three key shapes | 9H.4.2 checks user-minute and workspace-day before a model call on `/ai/chat`, `/ai/chat/stream`, `/ai/agent`, `/ai/agent/stream`, and `/ai/agent/resume` | Invent a second key prefix or read ids from the model |
| `None` when an id is blank | 9H.4.2 denies that AI call instead of billing `unknown` | Fall back to client IP |
| Token setting `0` and an unused `ai_tok` shape | Increment `ai_tok` only after a call returns usage metadata, and only when the setting is positive | Fail the request because usage metadata is missing |
| `remaining_budget` still `None` | Leave it unused; Redis is the store | Snapshot the counter onto `HarnessContext` |
| `budget_exceeded` still reserved | Over limit is HTTP 429 with `Retry-After` when known, or the existing SSE error object plus code `budget_exceeded`, then close. Between agent tool iterations, return `tool_error("budget_exceeded")` so 9H.3 wraps it | Add a second envelope or a new SSE event type |
| No Redis client | 9H.4.3 fail-opens on `RedisError` only, skips `/health` and `/health/ai`, and counts `allowed` / `denied` / `fail_open` with no user id label | Reuse `RateLimiter.check` or fail closed on a Redis outage |

`/ai/agent/reject` does not call the model, so it does not take a request from these counters. Threads and feedback do not either.

## Risks / Trade-offs

- [Defaults are mistaken for a live ceiling] → Comments in settings and `.env.example` say they are defaults and that this change does not enforce them. Routes stay unwired.
- [An operator sets the user-minute at or above 100] → Allowed. The spec constrains the default, not every override. 9H.4.2 still uses the configured integer.
- [A naive `datetime.now()` uses local time] → The builder requires an aware UTC datetime. Tests use a fixed UTC instant whose local date would differ in a negative offset.
- [9H.4.2 adds Redis `INCR` and a Redis error becomes HTTP 500] → The contract above says to catch Redis failures when the check appears. This change does not open a Redis connection, so the demo cannot fail that way yet.
- [Scope creep into 429 or cooldown] → Tasks stop at settings, key text, and unit tests.

## Migration Plan

1. Append the three settings and the example environment lines. Existing deploys keep working on the defaults with no Redis keys and no compose edit.
2. Add the key builders and unit tests.
3. Rollback is leaving the unused settings in place. Nothing is written to Postgres, Qdrant, or Redis, so there is no data to undo.

No open questions. Resume counts as a model call and reject does not; that is recorded for 9H.4.2 and is not work in this change.
