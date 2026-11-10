## Why

9H.4.2 already refuses an over-budget chat or agent completion and fail-opens when Redis errors, but that outcome is only a log line. Blueprint 9’s next locked substep is **9H.4.3** (`docs/documentation/blueprint/slice9_cost.md`): operators need a low-cardinality count of allows, denials, and fail-opens, and a proof that `/health` and `/health/ai` never touch the AI budget keys. The current `ai-harness-budget` spec still forbids a Prometheus series, which was the 9H.4.2 scope fence.

## What Changes

- **9H.4.3** — Each budget decision (`allowed`, `denied`, `fail_open`) increments one Prometheus counter. The only label is the outcome. User id, workspace id, and role are not labels.
- Redis errors still log a warning and allow the completion. An over-limit counter still denies and does not call the provider. Those behaviors stay as 9H.4.2 left them.
- `/health` and `/health/ai` stay unwired to the AI limiter. A test or source check shows those handlers do not read or write `ai_req`, `ai_day`, or `ai_tok`.
- **Out of scope:** incrementing `ai_tok` or enforcing `AI_TOKEN_BUDGET_PER_DAY`, a Langfuse budget attribute (the blueprint says “may”; this substep’s gate is the metric), provider cooldown, 9H.5, 9H.6’s grade claim, collapsing `/ai/chat*` into `/ai/agent*`, a second permission engine, Alembic, compose changes, Qdrant writes, Slice 8, Slice 9.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-harness-budget`: The requirement that forbids a Prometheus series for budget outcomes is replaced. Each decision is counted with an outcome label only. Fail-open, denial, and the health exclusion stay.

## Impact

- Code: the existing checker in `src/ai/harness/budget_check.py` records the outcome it already returns. The series lives with the other AI counters in `src/observability/metrics.py` (`dashnote_ai_*`). `src/ai/*` still does not import the Langfuse SDK. No new Redis commands.
- APIs: `/ai/chat*` and `/ai/agent*` both stay mounted. 429 and SSE `budget_exceeded` are unchanged. `/health` and `/health/ai` do not gain a budget dependency. Redis stays a soft dependency of the AI check and a hard dependency of `/health` only through the existing health checks.
- Tenancy: the metric cannot distinguish tenants. Role rules and workspace isolation do not change. Keys still use the server-bound user and workspace only.
- Dependencies: Prometheus `/metrics` already scrapes process counters. No Postgres or Qdrant change (`notes_chunks` / `files_chunks`). No Alembic migration. No new setting.
- Tests: a stubbed Redis error still proceeds and logs a warning; an over-limit counter still denies; the new series moves only on `outcome`. No live LLM key.
- Blueprint map: **9H.4.3 only**. On archive, drop the purpose-adjacent sentence that this capability must not add a budget series. Delta specs do not carry a new purpose for an existing capability.
