## Context

See proposal.md for why. Behavior contracts are in the `llm-resilience` and `ai-harness-degrade` deltas.

Today in `src/shared/llm/fallback.py`:
- `_skip: set[str]` permanently drops a candidate after model-gone **or** rate-limit (`_mark_gone`).
- `_candidates` filters `_skip`, then falls back to the full ordered list if every id was skipped.
- Timeouts walk without marking; non-429/non-gone exceptions (including most 5xx) raise immediately and do not walk.
- `reset_fallback_state()` clears `_cached_model` and `_skip` for tests (`tests/shared/test_llm_fallback.py`).
- Chat/agent already map total exhaustion (`LLMUnavailableError`) to 503 / SSE after 9H.5.1.

Process ownership stays on the API (and any worker process that imports the same module). No Redis. No route thinning. No Qdrant. No Alembic. No compose change.

## Goals / Non-Goals

**Goals:**

- Time-bounded cooldown for transient 429 / 5xx so a flaky primary does not exile itself for the process lifetime.
- Keep durable skip for model-gone / end-of-life.
- Same-request walk for 5xx that are treated as upstream (align with rate-limit walk), then skip that id on later requests while cooling.
- Preserve the existing all-candidates-unavailable contract and candidate order settings.

**Non-Goals:**

- Shared Redis cooldown across workers (document process-local).
- Harness control-plane module (9H.5.3).
- Changing AI budget keys, HITL, tool ACL, or health hard deps.
- Freezing a production cooldown integer in docs as law — settings default only.
- Counting a separate multi-failure counter before the first walk when a single 429/5xx already abandons the candidate (treat that abandon as the trigger).

## Decisions

### 1. Split durable skip from timed cooldown

**Choice:** Keep `_skip` for model-gone only. Add an in-process map `model_id → cooldown_until` (monotonic or UTC timestamp). `_candidates` excludes ids whose cooldown has not expired, then excludes durable `_skip`. Expired cooldown entries are dropped lazily when building the candidate list (or on read).

**Why:** Today rate-limit and gone share `_mark_gone`, which cannot expire. Blueprint 9H.5.2 requires re-eligibility. Mixing timers into `_skip` would either resurrect gone models or leave rate-limits permanent.

**Alternatives:** Reuse `_skip` with a parallel expiry dict keyed the same way (easy to call the wrong helper — rejected). Redis TTL keys (blueprint allows in-process; budget Redis is a different concern — rejected for this substep).

### 2. Enter cooldown when the walk abandons a candidate for 429 or 5xx

**Choice:** On `is_rate_limited(exc)`: walk to the next candidate and `_mark_cooldown(model)` instead of `_mark_gone`. On upstream 5xx (new helper, e.g. `is_upstream_server_error`): same walk + cooldown. Do not require a separate “N failures then cooldown” counter; the first abandon that already ends that candidate’s attempt is the trigger. Clear cooldown for a model on successful `_remember(model)`.

**Why:** Matches current rate-limit timing (mark when leaving the candidate) while fixing permanence. Aligns 5xx with the locked degrade matrix without inventing a second retry stack inside LiteLLM.

**Alternatives:** Cooldown only on the *next* HTTP request without same-request 5xx walk (weaker than rate-limit today — rejected). Wait for three 429s before cooling (extra state, blueprint does not lock N — deferred; default trigger is abandon-on-429/5xx).

### 3. Setting `LLM_PROVIDER_COOLDOWN_SECONDS` append-only

**Choice:** Append `LLM_PROVIDER_COOLDOWN_SECONDS: int = 60` (or similar safe default) on `Settings` next to LLM model settings. Comment that it is a default, not a production quota. Document in `.env.example` / production example if those files already list `LLM_MODEL*`. Cooldown duration ≤ 0 is treated as “no cooldown skip” only if needed for tests; prefer a positive default and monkeypatch in tests.

**Why:** Blueprint names the setting and refuses to lock the integer in the detail file. Append-only matches project infra law.

**Alternatives:** Hardcode 30s with no setting (operators cannot tune without a code change — rejected). Put cooldown in Redis with the same TTL (cross-worker consistency — out of scope).

### 4. Tests stay in `tests/shared/test_llm_fallback.py`; extend `reset_fallback_state`

**Choice:** Unit-test cooldown by stubbing candidate failures, asserting the next completion uses the fallback, then advancing time (or writing a past `cooldown_until`) and asserting the primary is tried again. Extend `reset_fallback_state` to clear the cooldown map. Do not require a live LLM key. Do not rewrite chat/agent routes for this substep unless a regression appears in existing unavailable mapping.

**Why:** Fallback ownership is already covered there. Route-level 503 is already proven by 9H.5.1.

**Alternatives:** Only HTTP-level tests (heavier, still needs stubs — optional later). New `tests/ai/test_harness_cooldown.py` that only re-exports shared tests (noise — rejected).

### 5. Leave routes and harness packages alone

**Choice:** No edits to `ai_routes/chat.py` / `agent.py` budget or HarnessContext wiring. No `src/ai/harness/control_plane.py`. Cooldown is entirely inside `shared.llm.fallback`.

**Why:** 9H.5.3 owns route thinning. Putting cooldown behind a half-built control plane creates a rename tax.

**Alternatives:** Expose cooldown through a new harness API used by routes (premature — rejected).

## Risks / Trade-offs

- [Multi-worker API replicas do not share cooldown] → Document process-local behavior; worst case each worker cools independently. Acceptable per blueprint fallback. Redis remains a later option, not this change.
- [Classifying 5xx too broadly walks on application bugs] → Limit the helper to HTTP 5xx / provider server errors analogous to `is_rate_limited`; do not treat every `Exception` as cooldown. Keep programming errors raising.
- [All candidates cooling falls back to full list today via `or list(ordered)`] → When filtering cooldown+skip leaves no candidates, raise `LLMUnavailableError` rather than immediately retrying cooling ids in a tight loop. Preserve a single pass; do not spin.
- [Existing rate-limit tests assume permanent skip] → Update `test_fallback_skips_rate_limited_primary` and related cases to assert cooldown semantics (skip while cooling, eligible after expiry).
- [Cached success model still points at a cooling id] → `_candidates` already reorders with `_cached_model` first; ensure cooling ids are filtered after that reorder so a cooling cache cannot win.

## Migration Plan

1. Append the setting and ship the fallback cooldown behavior in one API (and worker, if it imports fallback) deploy. No schema or compose change.
2. Operators who previously relied on a rate-limited id staying dead for the process lifetime will see it return after `LLM_PROVIDER_COOLDOWN_SECONDS`; tune the setting if a longer quiet period is needed.
3. Rollback reverts `fallback.py` + setting; durable `_skip` for rate-limit returns (previous behavior).

## Open Questions

None — default duration is an implementation default (propose 60s in tasks), not a spec-locked quota.
