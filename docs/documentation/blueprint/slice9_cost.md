# Slice 9H.4 — AI Budgets
## Composer substages (keys → 429/SSE → Redis fail-open)

> **Parent index (order source):** [`slice9_H.md`](slice9_H.md) — phase **9H.4**, calendar position 4th.  
> **Operator default:** [`../blueprint9.md`](../blueprint9.md).  
> **Code anchors:** `src/core/security/rate_limit.py` (pattern to mirror, not to replace) · `src/config.py` · `src/ai_routes/chat.py` · `src/ai_routes/agent.py` · `src/shared/llm/`  
> **Goal:** Stricter AI ceilings than the global API limit, with a controlled refusal and Redis fail-open.  
> **This file is a prompt blueprint.** Implementing the code is a later apply of these substages.

Order reminder: 9H.1 → 9H.2 → 9H.3 → 9H.4 → 9H.5 → 9H.6. Do not implement 9H.5 cooldown here.

Global limiter today: 100 requests/minute, fail-open on Redis errors. AI limits must be stricter. Exact integers are chosen at implementation time. This blueprint only names settings.

| Setting | Meaning |
|---------|---------|
| `AI_USER_REQUESTS_PER_MINUTE` | Per authenticated user, chat + agent calls. Must be an integer **below** the global 100/minute limit. |
| `AI_WORKSPACE_REQUESTS_PER_DAY` | Per workspace, calendar-day request cap. Integer chosen at implementation. |
| `AI_TOKEN_BUDGET_PER_DAY` | Optional. Enforced only when LiteLLM usage metadata is present on the call. Absent metadata → request ceilings alone are sufficient. |

---

## Sub-step 9H.4.1 — Settings and key shapes

**Goal:** Name counters and settings. Do not freeze production integers in the blueprint; code reads settings.

**Fallback:** If usage metadata is missing, skip the token counter for that call and still enforce request counters.

**Error boundary:** Identity comes from HarnessContext / JWT, never from the model. A missing user id does not fall back to a shared “anonymous AI” bucket for an authenticated route; unauthenticated calls never reach these routes.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.4.1 — AI budget settings and Redis key shapes.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: HarnessContext exists (9H.1.2) so keys use trusted ids.

GOAL:
  Add settings AI_USER_REQUESTS_PER_MINUTE, AI_WORKSPACE_REQUESTS_PER_DAY,
  and optional AI_TOKEN_BUDGET_PER_DAY. Append-only on settings and env examples.
  Key shapes:
    ai_req:{user_id}:{minute_bucket}
    ai_day:{workspace_id}:{day_bucket}
    ai_tok:{workspace_id}:{day_bucket}   # only when usage metadata exists
  Values must be configurable. User-per-minute must be stricter than global 100/minute.
  Do not hardcode a "final" production integer in docs as if it were spec law.
  Pick a safe default in settings only when you implement, and document it as a default.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT key budgets off model-supplied workspace or user ids.

VALIDATION GATE:
  Settings load in tests. A comment or env example names all three variables.
  The user-minute default is an integer lower than 100.

FALLBACK:
  When the provider returns no usage metadata, do not increment ai_tok and do not fail the request
  for that reason. Request counters still apply.

ERROR BOUNDARY:
  Authenticated routes with no user id in context do not share one global AI key.
  Deny the AI call (controlled error) rather than billing "unknown" to another tenant.
```

---

## Sub-step 9H.4.2 — 429 and SSE contract

**Goal:** Over budget is a client-visible limit, not a 500 and not a model hallucination about quotas.

**Fallback:** Non-streaming routes return HTTP 429 with `Retry-After` when a window end is known. Streaming routes emit the existing SSE error shape plus a stable code `budget_exceeded`, then close the stream. Do not hold the stream open.

**Error boundary:** The check happens before the model call. A denied request does not spend a provider completion.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.4.2 — Controlled over-budget response.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.4.1 counters exist.

GOAL:
  Before a chat or agent model call, check the user-minute and workspace-day counters.
  When over limit:
    POST /ai/chat and POST /ai/agent return HTTP 429 with Retry-After when known.
    Streaming routes emit an SSE error that includes code budget_exceeded and retry guidance,
    then end the stream.
  Do not call the LLM provider on that request.
  Map the tool/harness code budget_exceeded reserved in 9H.2 when the check fires
  inside an agent turn between tool iterations as well.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT return HTTP 500 for a normal over-budget result.

VALIDATION GATE:
  A test with a tiny limit returns 429 or the SSE budget_exceeded error and asserts
  the model client was not called.

FALLBACK:
  If Retry-After cannot be computed, omit the header and still return 429 / SSE error
  with a fixed "retry shortly" message. Never 500 to compensate.

ERROR BOUNDARY:
  Budget denial is fail closed for that request. No partial generation.
```

---

## Sub-step 9H.4.3 — Redis fail-open, health, metrics

**Goal:** Redis trouble does not take down AI or health. Successful checks still limit spend.

**Fallback:** On Redis connection, timeout, or provider quota errors inside the AI budget check: log a warning and allow the request. Do not allow-list this behavior for application bugs (bad key schema). Only Redis failures.

**Error boundary:** `/health` and `/health/ai` never call the AI budget limiter. Prometheus may count allows, denies, and fail-opens with low-cardinality labels (outcome only, no user id).

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.4.3 — Fail open on Redis, exclude health, count outcomes.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.4.2 denial path exists.

GOAL:
  Mirror core.security.rate_limit fail-open: Redis errors log a warning and allow
  the AI request. Over-limit still denies.
  GET /health and GET /health/ai do not touch AI budget keys.
  Add a low-cardinality metric for AI budget outcomes (allowed, denied, fail_open).
  Trace attribute on the existing Langfuse path may record budget outcome; do not
  import the Langfuse SDK inside src/ai/*.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT fail closed on Redis outages (that recreates the health-check outage).

VALIDATION GATE:
  A unit test stubs a Redis error and expects the request to proceed plus a warning.
  A unit test stubs an over-limit counter and expects denial.
  A health-route test or code inspection shows health handlers are not wired to the AI limiter.

FALLBACK:
  If Prometheus registration is awkward in the substep, log the outcome with a stable
  event name and file a one-line follow-up. Do not skip the fail-open test.

ERROR BOUNDARY:
  The limiter function catches Redis failures only. Unexpected programming errors
  still surface in tests. Do not blanket-except Exception and hide bugs without a log.
```
