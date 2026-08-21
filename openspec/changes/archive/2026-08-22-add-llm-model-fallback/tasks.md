## 1. Settings and shared LLM helper

- [x] 1.1 Append `LLM_MODEL_FALLBACKS` on Settings with a documented default candidate list; add `llm_model_candidates` property. Change default `LLM_MODEL` in `src/config.py` and `.env.example` to `nvidia_nim/nvidia/nemotron-3-nano-30b-a3b`.
- [x] 1.2 Add `shared/llm/fallback.py`: detect model-gone, walk candidates, cache winner, `acompletion_with_fallback` (stream and non-stream). Export from `shared/llm/__init__.py`.
- [x] 1.3 Add `tests/shared/test_llm_fallback.py` (mock 410 then success; all-gone raises; no live HTTP).

## 2. Call sites, health, routes

- [x] 2.1 Wire RAG `answer` / `stream_answer` and agent `call_model` (plus structured path via shared helper) to `acompletion_with_fallback`.
- [x] 2.2 Soft-resolve a candidate in API and worker lifespan without blocking boot.
- [x] 2.3 Extend `GET /health/ai` with soft `dependencies.llm`; keep `GET /health` db+redis only. Add/adjust tests so LLM down does not fail hard health.
- [x] 2.4 Chat and agent SSE exhausted-fallback `error.message` is exactly `LLM temporarily unavailable; retry shortly`. Extend `tests/ai/test_agent_retry.py` (or sibling) for gone-after-fallback.

## 3. Docs and operator config

- [x] 3.1 Write `docs/documentation/issue_solve.md` (problem, 410 timeline, permanent fallback, recreate api/worker). No secrets or passwords.
- [x] 3.2 Update `docs/nvidia.md` and `docs/documentation/ai.md` away from retired default ids.
- [x] 3.3 Point local `.env` `LLM_MODEL` at nano and set `LLM_MODEL_FALLBACKS`; recreate `api` and `worker` so the running stack picks up code+env.
