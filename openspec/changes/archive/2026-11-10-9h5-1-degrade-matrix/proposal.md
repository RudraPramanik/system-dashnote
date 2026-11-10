## Why

9H.1–9H.4 already bind tenant, enforce tool ACL, treat retrieved text as data, and refuse over-budget completions. Blueprint 9’s next locked substep is **9H.5.1** (`docs/documentation/blueprint/slice9_resilience.md`, indexed by `slice9_H.md`): the three runtime degrade rows (providers exhausted, checkpointer down, budget exhausted) must be true and tested together, without silent empty 200s or mutations that commit when HITL cannot resume. Pieces exist in fallback, HITL guards, and budget refusal, but unary `/ai/chat` still lacks a first-class provider-unavailable mapping, and checkpointer-down proof stops at the probe string rather than a no-commit assertion.

## What Changes

- **9H.5.1** — Encode the locked degrade matrix (except provider cooldown, which is 9H.5.2):
  - All model providers exhausted after the existing fallback walk → user-safe unavailable: HTTP **503** on unary chat/agent, or SSE `type: "error"` with the existing unavailable message on streams. Never a silent empty HTTP 200.
  - Approval checkpointer unavailable → `create_note` / `update_note` do not commit; search-style tools may still answer (or return the empty-retrieval copy).
  - AI budget exhausted → keep the existing 9H.4 refusal (429 / SSE `budget_exceeded`); no provider completion.
- Close gaps where chat unary can still surface provider exhaustion as a generic 500, and where checkpointer-down tests do not yet assert that NoteService was not called.
- Keep `/ai/chat*` and `/ai/agent*` both mounted. No second agent framework. No control-plane route thinning (9H.5.3). No provider cooldown store (9H.5.2).
- **Out of scope:** `LLM_PROVIDER_COOLDOWN_SECONDS`, harness control-plane module, 9H.6 grade claims, collapsing chat into agent, a second permission engine, Alembic, compose changes, Qdrant writes, Slice 8, Slice 9, billing.

## Capabilities

### New Capabilities

- `ai-harness-degrade`: Runtime degrade matrix for the workspace assistant — provider-down unavailable responses, checkpointer-down mutation fail-closed with search allowed, and budget-down reuse of the existing AI budget refusal — with fixture/unit proof that does not need a live model key.

### Modified Capabilities

- `llm-resilience`: Extend the “all candidates unavailable” contract so unary `POST /ai/chat` returns HTTP 503 with the same user-safe unavailable message (not a silent empty 200 and not a bare 500 for that exhaustion case), matching the agent unary and stream paths.

## Impact

- Code: `src/ai_routes/chat.py` (map `LLMUnavailableError` / exhausted fallback on unary chat), existing guards in `src/ai/tools/note_tools.py` and agent route 503/SSE mapping stay the source of truth where already correct; possibly small shared helper only if it avoids duplicating the unavailable message. `src/shared/llm/fallback.py` stays the fallback walk. No ARQ worker change. No Redis cooldown. No new compose service.
- APIs: `/ai/chat*` and `/ai/agent*` both remain. Unary chat gains an explicit 503 on total provider failure. Streams keep SSE error frames. Budget 429 / `budget_exceeded` unchanged. `/health` and `/health/ai` stay independent of AI budget keys; checkpointer remains a soft `/health/ai` probe.
- Tenancy: workspace isolation and note role checks from 9H.1–9H.3 stay in force. Degrade modes do not invent a tenant or skip HITL.
- Dependencies: no Alembic, no settings append for cooldown, no Qdrant (`notes_chunks` / `files_chunks`) change, no Langfuse SDK inside `src/ai/*`.
- Tests: provider-unavailable on chat unary and an existing stream/agent path; checkpointer-down asserts no note commit and that search may still run; budget row covered by pointing at existing budget-refusal tests (no live LLM key).
- Blueprint map: **9H.5.1 only**.
