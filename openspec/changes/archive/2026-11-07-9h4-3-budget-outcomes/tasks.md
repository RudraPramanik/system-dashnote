## 1. Outcome counter (observability)

- [x] 1.1 Add `dashnote_ai_budget_outcome_total` and `inc_ai_budget_outcome(outcome)` in `src/observability/metrics.py`. The only label is `outcome`. Accept only `allowed`, `denied`, and `fail_open`. Ignore any other string so it cannot create a label
- [x] 1.2 Export the increment from `src/observability/__init__.py` next to the other AI counters. Do not add a user, workspace, or role label

## 2. Checker (API)

- [x] 2.1 In `consume_ai_request_budget`, call `inc_ai_budget_outcome` once immediately before every return, including blank-id denial, missing Redis, `RedisError`, allow, and over-limit denial. Do not add a second increment in chat routes or `call_model`
- [x] 2.2 Import only `inc_ai_budget_outcome` from `observability.metrics`. Do not import the Langfuse SDK, `observability.tracing`, or `core`. Do not add a Redis command or write `ai_tok`

## 3. Worker and other surfaces stay put

- [x] 3.1 Do not call the checker or the new increment from the ARQ worker, `deep_health`, `ai_health`, `/ai/agent/reject`, thread routes, or feedback. Do not edit Alembic, `docker-compose.yml`, Qdrant (`notes_chunks` / `files_chunks`), or the global limiter
- [x] 3.2 Do not increment token usage, add a Langfuse attribute, or implement 9H.5 or 9H.6

## 4. Proof

- [x] 4.1 Extend `tests/observability/test_metrics.py` so one allowed, one denied, and one fail-open sample appear on `dashnote_ai_budget_outcome_total`, and that series text has no `user_id`, workspace id, or `role` label
- [x] 4.2 Extend `tests/ai/test_harness_budget_refusal.py`: a `RedisError` still fail-opens with a warning and increments `fail_open`; an over-limit counter still denies, does not call the model, and increments `denied`; two different user and workspace ids on allow share that same series
- [x] 4.3 Assert the source of `deep_health` and `ai_health` does not reference `consume_ai_request_budget`, `ai_req`, `ai_day`, or `ai_tok`
- [x] 4.4 Run `python -m pytest tests/observability/test_metrics.py tests/ai/test_harness_budget_refusal.py tests/ai/test_harness_budget.py -q` with no live LLM key. Do not weaken the 9H.4.2 refusal tests to go green
