## Why

9H.5.1 already maps total provider exhaustion to a user-safe 503 / SSE error and keeps checkpointer-down mutations fail-closed. Today `acompletion_with_fallback` still treats a rate-limited id like a permanently gone model (`_mark_gone`), so a transient 429 can exile that candidate for the life of the API process and stampede every later request onto the remaining hatch. Blueprint 9’s next locked substep is **9H.5.2** (`docs/documentation/blueprint/slice9_resilience.md`, indexed by `slice9_H.md`): after repeated 429 / 5xx on one model id, cool it down briefly, keep walking `LLM_MODEL` / `LLM_MODEL_FALLBACKS`, then make it eligible again when the timer ends.

## What Changes

- **9H.5.2** — Provider cooldown, then the existing fallback walk:
  - After repeated HTTP 429 or 5xx from one LiteLLM model id, mark that id cooling down for a short, configurable window (`LLM_PROVIDER_COOLDOWN_SECONDS`, default chosen at implement time; not a frozen production quota).
  - While cooling, the next completion skips that id and continues the existing candidate order.
  - When the cooldown expires, the id is eligible again (unlike today’s permanent `_skip` for rate-limit).
  - Model-gone / end-of-life may keep a durable skip; cooldown is for transient rate-limit and upstream 5xx, not for rewriting the gone path into a timer.
  - If every candidate is cooling down or failing, keep the existing user-safe unavailable response (`LLMUnavailableError` → 503 / SSE error). Do not loop forever.
- Store cooldown in-process on the API worker. Document that multiple workers do not share it. Do not require Redis for cooldown (budget Redis stays a different concern).
- Keep `/ai/chat*` and `/ai/agent*` both mounted. No second agent framework. No harness control-plane thinning (9H.5.3). No 9H.6 grade claims.
- **Out of scope:** control-plane module, fixture grade-claim gate, collapsing chat into agent, a second permission engine, Alembic, compose changes, Qdrant writes, Slice 8, Slice 9, billing, AI budget key changes.

## Capabilities

### New Capabilities

<!-- none — cooldown extends existing LLM / degrade capabilities -->

### Modified Capabilities

- `llm-resilience`: Replace permanent process-lifetime exile of rate-limited (and add repeated 5xx) candidates with a time-bounded cooldown that still walks `LLM_MODEL` / `LLM_MODEL_FALLBACKS`, re-admits the id after expiry, and keeps the all-candidates-unavailable contract.
- `ai-harness-degrade`: Add the locked degrade-matrix cooldown row (repeated 429/5xx → short skip → existing fallback) and drop the 9H.5.1 clause that deferred provider cooldown out of that capability.

## Impact

- Code: primarily `src/shared/llm/fallback.py` (cooldown map vs permanent `_skip` for rate-limit/5xx; settings append for `LLM_PROVIDER_COOLDOWN_SECONDS`). Chat and agent routes keep mapping total exhaustion the same way; no route rewrite. No ARQ worker change required unless the worker already shares this module’s process state (same in-process semantics).
- APIs: `/ai/chat*` and `/ai/agent*` both remain. No new status codes beyond the existing 503 / SSE unavailable path when every candidate is cooling or failing. `/health` and `/health/ai` stay independent of cooldown Redis (there is none). Soft `/health/ai` may still show configured vs cached model; cooldown does not invent a new health hard dependency.
- Tenancy: workspace isolation, HITL, tool ACL, and AI budgets from 9H.1–9H.4 stay in force. Cooldown keys off model id only, never tenant.
- Dependencies: append-only settings / env examples. No Alembic, no compose service, no Qdrant (`notes_chunks` / `files_chunks`) change, no Langfuse SDK inside `src/ai/*`, no Redis cooldown keys.
- Tests: unit coverage that a primary in cooldown yields the next fallback completion, and that after expiry the primary is tried again; all-cooling maps to the existing unavailable error. No live LLM key.
- Blueprint map: **9H.5.2 only**.
