## Why

NVIDIA hosted NIM ids keep returning HTTP 410 Gone (Mistral Medium 3.5 EOL 2026-08-07; `z-ai/glm-5.2` EOL 2026-08-21). Chat and agent still look like a frontend bug: streams return HTTP 200 plus SSE `type: "error"` with `"Stream encountered an error. Please try again."` while `GET /health` and `GET /health/ai` stay 200 because they never probe the LLM. Pinning a single `LLM_MODEL` is not a lasting fix.

## What Changes

- Add `LLM_MODEL_FALLBACKS` (comma-separated LiteLLM ids). On 410 / EOL / model-not-found, try the next candidate for chat, agent, and structured completions — including `stream=True`.
- Soft-resolve a working model at API/worker startup (non-blocking). Cache the winner; invalidate and re-resolve on the next 410.
- Extend `GET /health/ai` with a **soft** LLM probe (`dependencies.llm`). Hard `GET /health` stays Postgres + Redis only.
- When every candidate fails, chat/agent SSE `error.message` MUST use the existing calm copy `"LLM temporarily unavailable; retry shortly"` (not the generic stream sentence) so DashNotes 503/unavailable UX can match.
- Document the outage and operator steps in `docs/documentation/issue_solve.md`. Update `.env.example`, `docs/nvidia.md`, and `docs/documentation/ai.md` defaults away from retired ids.
- **Not BREAKING.** No route removals. Chat and agent continue to coexist.

## Capabilities

### New Capabilities

- `llm-resilience`: Runtime LLM candidate list, 410 fallback, startup resolve, and user-visible stream error copy when no candidate works.

### Modified Capabilities

- `production-platform`: `GET /health/ai` MUST report a soft LLM dependency in addition to Qdrant, and MUST still never fail the hard deploy `/health` gate.

## Impact

- **Code:** `src/config.py` (append-only settings), `src/shared/llm/` (gone-detection + fallback completion), `src/ai/services/rag_service.py`, `src/ai/workflows/workspace_assistant.py`, `src/ai_routes/chat.py` / `agent.py` (SSE copy), `src/core/health.py`, `src/main.py` and worker lifespan (soft resolve).
- **Config:** `.env.example` (`LLM_MODEL`, `LLM_MODEL_FALLBACKS`). Local `.env` is operator-owned; docs describe recreate of `api` + `worker`.
- **Docs:** `docs/documentation/issue_solve.md`, `docs/nvidia.md`, `docs/documentation/ai.md`.
- **Tests:** `tests/shared/` and `tests/ai/` — no live provider calls; mock 410 then success on fallback.
- **Tenancy:** Unchanged. Fallback never reads `workspace_id` from the model.
- **Non-goals:** Do not collapse `/ai/chat*` into `/ai/agent*`. Do not make LLM a hard `/health` dependency. Do not call NVIDIA `/v1/models` as the sole resolver (account entitlement ≠ catalog listing).
