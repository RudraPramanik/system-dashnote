## Why

9H.1–9H.5.2 already bind tenant, enforce tool ACL and injection hygiene, refuse over-budget completions, map provider exhaustion to 503 / SSE, keep checkpointer-down mutations fail-closed, and cool down failing model ids. Budget check, `HarnessContext` construction, and provider-unavailable mapping are still copy-pasted across `ai_routes/chat.py` and `ai_routes/agent.py`, so denials can drift and routes stay thick. Blueprint 9’s next locked substep is **9H.5.3** (`docs/documentation/blueprint/slice9_resilience.md`, indexed by `slice9_H.md`): one harness control plane that both AI surfaces call for “may I run, then run,” with routes left as HTTP / SSE parsers.

## What Changes

- **9H.5.3** — Thin routes, one harness control plane:
  - Introduce one harness module (name locked in design) that owns trusted-context construction, AI budget check, and provider-unavailable / known-denial mapping for chat and agent.
  - `/ai/chat*` and `/ai/agent*` both call that module instead of reimplementing Redis budget keys, `HarnessContext` bind, or 429 / 503 / SSE denial mapping inline.
  - Two entrypoints in the same module (`run_chat` / `run_agent`, or unary/stream pairs) are acceptable; copy-pasting the budget check into both route files is not.
  - LangGraph workspace assistant stays the agent loop. `RagService` stays the fast RAG path. Cooldown stays inside `shared.llm.fallback` (9H.5.2).
  - Routes catch harness denials and map them to 429, 403, or 503 (or the matching SSE error). Those known denials MUST NOT fall through a catch-all into 500.
- Keep `/ai/chat*` and `/ai/agent*` both mounted. No second agent framework. No 9H.6 grade claims.
- **Out of scope:** fixture grade-claim gate (9H.6), collapsing chat into agent, a second permission engine, Alembic, compose changes, Qdrant writes, Slice 8, Slice 9, billing, rewriting cooldown or HITL probe ownership, Langfuse SDK imports inside `src/ai/*`.

## Capabilities

### New Capabilities

- `ai-harness-control-plane`: One harness entry that chat and agent routes use for budget gate, trusted tenant context, and typed denial mapping; routes stay thin HTTP/SSE adapters over existing RagService and LangGraph.

### Modified Capabilities

- `ai-harness-degrade`: Drop the 9H.5.1/9H.5.2 fence that a single harness control-plane module MUST NOT be required; degrade rows remain, now reachable through the shared plane rather than duplicated route logic.

## Impact

- Code: new module under `src/ai/harness/` (exact name in design); thin `ai_routes/chat.py` and `ai_routes/agent.py` so they no longer own inline Redis budget key usage or duplicate denial mapping. Existing `budget_check.py`, `context.py`, and `shared.llm.fallback` stay the implementations behind the plane. No ARQ worker rewrite. No Qdrant (`notes_chunks` / `files_chunks`) change.
- APIs: `/ai/chat*` and `/ai/agent*` both remain. Client-visible contracts for 429 / `budget_exceeded`, 503 / LLM unavailable, HITL approval events, and citations stay the same. `/health` and `/health/ai` stay independent of AI budget keys.
- Tenancy: workspace / user / role still freeze from JWT into `HarnessContext` (9H.1). Tool ACL and injection hygiene (9H.2–9H.3) stay on tools / prompts.
- Dependencies: no Alembic, no compose service, no new Redis key scheme, no Langfuse SDK inside `src/ai/*`.
- Tests: prove routes no longer instantiate budget checks inline; a harness denial is what produces 429 or 503; existing chat citation and agent HITL suites still pass. No live LLM key.
- Blueprint map: **9H.5.3 only**.
