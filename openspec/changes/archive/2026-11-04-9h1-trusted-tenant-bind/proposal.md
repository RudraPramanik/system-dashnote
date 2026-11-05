## Why

Agent tools still trust the model to pass `workspace_id`, `user_id`, and `role` via tool schemas and the system prompt. That honor-system tenancy is the first locked gap in Blueprint 9 (`9H.1`): without a server-bound HarnessContext, later ACL, budget, and golden phases cannot key off trusted identity. Blueprint docs are already authored; this change implements the runtime bind.

## What Changes

- Introduce a trusted `HarnessContext` (workspace, user, role, plus trace / budget placeholders as needed) built from JWT `RequestContext` and stored once per agent invoke.
- Inventory then remove or overwrite model-supplied tenant fields on search / create / update / summarize tools so `NoteService` / `RagService` only see session identity.
- Ensure HITL `approval_required` payloads carry server-bound tenant identity, not raw model JSON; resume/reject cross-workspace denial stays fail-closed.
- Add a fixture or focused unit golden proving an invented foreign `workspace_id` is not passed through to services.
- **Out of scope:** 9H.2 tool ACL envelopes, 9H.3 injection delimiters, 9H.4 AI budgets, 9H.5 degrade/control plane, 9H.6 full grade proof suite, chat-route refactors, multi-agent Slice 9, GraphRAG Slice 8.

## Capabilities

### New Capabilities

- `ai-harness-trust`: Runtime trusted-tenant bind for the LangGraph agent — HarnessContext construction, tool tenant freeze (schema omit or overwrite), fail-closed missing context, and invented-workspace regression coverage.

### Modified Capabilities

- `agent-hitl`: Approval payloads for create/update MUST expose tenant fields from the bound HarnessContext (server-authored), not from model-echoed tool args; existing interrupt / resume / reject workspace ownership rules remain.

## Impact

- Code: `src/ai/tools/schemas.py`, `src/ai/tools/note_tools.py`, `src/ai/workflows/workspace_assistant.py` (and related state/graph invoke wiring), `src/ai_routes/agent.py` as needed to inject context; tests under `tests/` mirroring tools/workflows; optional fixture under evals if the trajectory runner can express it without a live LLM key.
- APIs: `/ai/agent*` behavior hardens; `/ai/chat*` untouched. Preferred path may **BREAKING**-change tool argument schemas by omitting tenant fields (clients that inspect tool schemas see fewer args; product UI must not send tenant ids on resume/reject today and stays fine).
- No Alembic, Redis budget keys, compose rewrite, or second permission engine.
- Blueprint map for this change: **9H.1.1 → 9H.1.2 → 9H.1.3 → 9H.1.4** only (`docs/documentation/blueprint/slice9_trust.md`). Next after this change: **9H.2** (`slice9_policy.md`).
