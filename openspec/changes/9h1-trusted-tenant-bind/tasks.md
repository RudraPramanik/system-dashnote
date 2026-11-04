## 1. Inventory (9H.1.1)

- [x] 1.1 List every tool schema field and system-prompt sentence that asks the model to supply `workspace_id`, `user_id`, or `role` (search, create, update, summarize) in a short inventory table under the change notes or a tracked comment — no runtime behavior change
- [x] 1.2 Note any eval fixtures, scripts, or tests that pass tenant tool args so bind work can update them

## 2. HarnessContext + bind (9H.1.2)

- [x] 2.1 Add `HarnessContext` (workspace, user, role; optional trace/budget placeholders) under `src/ai/` and a ContextVar parallel to `db_session_var`
- [x] 2.2 Build HarnessContext from JWT `RequestContext` in `ai_routes/agent.py` invoke/stream paths; store on graph state and set the ContextVar for the tool-execution node
- [x] 2.3 Prefer removing tenant fields from `schemas.py` / tool signatures; wrappers read tenant only from HarnessContext before `NoteService` / `RagService` (overwrite + mismatch log if schemas must stay)
- [x] 2.4 Update `workspace_assistant.py` system prompt so it no longer instructs the model to pass tenant fields
- [x] 2.5 Missing HarnessContext → deny tool result (fail closed); do not guess workspace from the user message
- [x] 2.6 Confirm `/ai/chat*` routes are untouched

## 3. HITL bound identity (9H.1.3)

- [x] 3.1 When emitting `approval_required` for create/update, copy tenant fields into `args` from HarnessContext (keep existing JSON keys; mark server-authored)
- [x] 3.2 Verify resume/reject still deny cross-workspace `thread_id` with existing 403 behavior; re-run existing HITL tests

## 4. Invented-workspace proof (9H.1.4)

- [x] 4.1 Add a focused pytest under `tests/` that feeds a foreign `workspace_id` into the tool path and asserts the service receives session workspace only (or deny) — no live LLM key
- [x] 4.2 If the eval fixture runner can express the same theme without a provider key, add the fixture; otherwise document that the unit test covers the 9H.1.4 theme
- [x] 4.3 Run `python -m pytest` on the new/updated harness-trust and HITL tests `-q` and fix regressions from schema/prompt changes
