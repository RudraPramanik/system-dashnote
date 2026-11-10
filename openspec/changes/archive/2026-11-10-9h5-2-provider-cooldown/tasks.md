## 1. Settings

- [x] 1.1 Append `LLM_PROVIDER_COOLDOWN_SECONDS: int = 60` on `Settings` in `src/config.py`, next to the existing `LLM_MODEL` / `LLM_MODEL_FALLBACKS` settings. Comment that this is a default for transient 429/5xx cooldown, not a frozen production quota, and that cooldown is process-local (not Redis)
- [x] 1.2 Name `LLM_PROVIDER_COOLDOWN_SECONDS` in `.env.example` (and `.env.production.example` if that file already lists `LLM_MODEL*`) with the same default and a one-line comment. Do not edit `docker-compose.yml`, Alembic, or Qdrant collections

## 2. Cooldown in shared LLM fallback

- [x] 2.1 In `src/shared/llm/fallback.py`, add an in-process cooldown map (`model_id → expiry`) separate from durable `_skip`. Extend `reset_fallback_state()` to clear the cooldown map. Do not use Redis
- [x] 2.2 Filter cooling ids inside `_candidates` after cache reorder so a cooling `_cached_model` cannot win. Lazily drop expired entries. If every candidate is cooling or durably skipped, do not tightly re-loop the cooling set — raise `LLMUnavailableError` after one exhausted pass
- [x] 2.3 On rate-limit (`is_rate_limited`), walk to the next candidate and mark cooldown instead of `_mark_gone`. Keep `_mark_gone` for model-gone / end-of-life only. Clear cooldown for a model in `_remember` on success
- [x] 2.4 Add `is_upstream_server_error` (HTTP 5xx / equivalent provider server error). On match, walk to the next candidate and mark cooldown the same way as rate-limit. Do not treat arbitrary `Exception` as cooldown. Do not implement 9H.5.3 control-plane route thinning

## 3. Surfaces that stay put

- [x] 3.1 Do not rewrite `ai_routes/chat.py` or `ai_routes/agent.py` for cooldown. Keep existing 503 / SSE unavailable mapping from 9H.5.1. Do not touch AI budget keys, HITL, tool ACL, `HarnessContext`, Alembic, `docker-compose.yml`, or Qdrant (`notes_chunks` / `files_chunks`)
- [x] 3.2 Do not implement 9H.5.3 control plane or 9H.6 grade claims. Do not collapse `/ai/chat*` into `/ai/agent*`

## 4. Proof

- [x] 4.1 Extend `tests/shared/test_llm_fallback.py`: after a primary 429 (or 5xx) with a live fallback, the next completion skips the primary while cooling and uses the fallback. After forcing expiry (past `cooldown_until` or monkeypatched clock), the primary is eligible again
- [x] 4.2 Update existing rate-limit tests that assumed permanent `_skip` so they assert cooldown semantics. Add a case where every candidate is cooling or failing and `LLMUnavailableError` is raised without an infinite loop
- [x] 4.3 Assert settings default `LLM_PROVIDER_COOLDOWN_SECONDS == 60` (or the chosen positive default) and that `.env.example` names the variable
- [x] 4.4 Run `python -m pytest tests/shared/test_llm_fallback.py tests/ai/test_harness_degrade.py tests/ai/test_agent_retry.py -q` with no live LLM key. Do not skip cooldown assertions to go green
