## Context

See proposal.md for why NVIDIA hosted ids keep 410-ing. Today `RagService.stream_answer` calls `litellm.acompletion(..., stream=True)` with `settings.LLM_MODEL` only; exceptions become a generic SSE error. Agent `call_model` uses `acompletion_with_retry` on the same single id. `GET /health/ai` probes Qdrant only. `configure_litellm_env` already runs at API and worker boot.

Constraints: append-only settings; `from config import get_settings`; no Langfuse inside `src/ai/*`; LLM must stay a soft dependency; chat ≠ agent.

## Goals / Non-Goals

**Goals:**
- One shared completion helper that walks candidates on model-gone, including streaming.
- Soft LLM status on `/health/ai`.
- Operator-facing incident doc without secrets.

**Non-Goals:**
- Auto-discovering the full NVIDIA catalog as the source of truth.
- Changing embedding models or Qdrant dimensions.
- Frontend Playwright B-gate rewrites (DashNotes is out of this repo's allowed edit root).
- Making LLM part of hard `/health` or default smoke.

## Decisions

1. **Candidate list in settings, not catalog scrape**  
   `LLM_MODEL` + `LLM_MODEL_FALLBACKS`. Catalog listing does not mean the account can call the id (seen 404-while-listed).  
   Alternative: GET `/v1/models` and pick first — rejected as entitlement-unsafe.

2. **Detect gone from exception text/status, then retry the same payload**  
   Treat 410, "end of life", "no longer available", and LiteLLM `NotFoundError` as model-gone. Do not retry gone on the same id. Transient RateLimit/Timeout still use existing `acompletion_with_retry`.  
   Alternative: only restart containers after editing `.env` — that is what failed twice.

3. **In-process cache of the winning model**  
   After a successful completion (or a cheap startup probe), reuse the winner until the next gone error. Startup probe is best-effort and must not delay boot past a short timeout.  
   Alternative: probe every request — extra latency and quota.

4. **Central helper in `shared/llm/`**  
   `acompletion_with_fallback` wrapping `litellm.acompletion` / existing retry helper. Call sites: RAG (stream + non-stream), agent `call_model`, structured completions already going through `shared/llm`.  
   Alternative: duplicate fallback in each router — rejected.

5. **SSE copy change only when fallbacks exhaust**  
   Message exactly `LLM temporarily unavailable; retry shortly` so DashNotes existing unavailable handling can match. Keep HTTP 200 for the stream envelope (current contract); do not invent a new event type.

6. **`/health/ai` LLM probe is a tiny non-stream completion with a short timeout**  
   Report `reachable` + `model` (winning id, never the API key). If no candidate works: `reachable: false`, overall status `degraded` if Qdrant is otherwise ok.

7. **Default fallbacks** (documented, pinged live 2026-08-21):  
   `nvidia_nim/nvidia/nemotron-3-nano-30b-a3b`, `nvidia_nim/nvidia/nemotron-3-super-120b-a12b`, `gemini/gemini-2.5-flash`. Default `LLM_MODEL` in `.env.example` becomes nano, not Mistral/GLM 5.2.

## Risks / Trade-offs

- **[Risk] First request after EOL pays N failed 410s** → Mitigation: startup resolve + cache; skip already-failed ids for the process lifetime.
- **[Risk] Fallback model weaker at tool calling** → Mitigation: prefer NIM instruct models first; Gemini last. Document that operators can reorder the list.
- **[Risk] Health probe consumes quota** → Mitigation: max_tokens=8, timeout a few seconds, never on `/health`.
- **[Risk] Streaming iterator 410 after headers** → Mitigation: treat exceptions during `acompletion(..., stream=True)` setup the same as non-stream; if the iterator fails mid-token, still walk remaining candidates for a new stream when no tokens were yielded.

## Migration Plan

1. Ship code with defaults; operators add `LLM_MODEL_FALLBACKS` and recreate `api` + `worker`.
2. Local `.env`: set `LLM_MODEL` to a live candidate (nano) so the first hop is cheap.
3. Rollback: remove fallbacks setting (empty string) and pin `LLM_MODEL` — behavior returns to single-id (broken if that id is gone).

## Open Questions

None that block implementation. Account-specific NIM entitlements stay an operator concern.
