## Why

9H.1 binds workspace, user, and role on agent tools, but those tools still do not apply the note role rules that `notes/permissions.py` already enforces on the REST API. A member can be offered HITL for an update they could not perform via `PATCH /notes/{id}`, and tool failures are ad-hoc strings (sometimes with `str(exception)`). Blueprint 9’s next locked phase is **9H.2** (`docs/documentation/blueprint/slice9_policy.md`): same owner/admin vs member rules, one stable error envelope, and a deny path that never commits.

## What Changes

- **9H.2.1** — Before search, summarize, create, or update call `RagService` or a mutating `NoteService` method, enforce the existing note role rules using `HarnessContext.role`. Unknown roles fail closed. `create_note` and `update_note` still interrupt before commit when the role is allowed. A member who cannot manage a note is denied before HITL is offered.
- **9H.2.2** — Failed tool results use one stringified JSON envelope with codes `forbidden`, `not_found`, `budget_exceeded`, `approval_required`, and `upstream`. Success stays a normal tool result. `budget_exceeded` is reserved and unused. `approval_required` stays the existing HITL pause, not a committed write and not a new SSE event type.
- **9H.2.3** — An automated deny-path test: a role `notes/permissions.py` would reject receives `forbidden`, HITL does not complete into a write, and no note row or vector write runs. No live LLM key.
- Upgrade the 9H.1 missing-harness denial to that same `forbidden` envelope so there is one fail-closed shape.
- **Out of scope (hint only, in design):** 9H.3 delimiters, instruction hierarchy, and poisoned-content goldens. 9H.4 Redis budgets beyond reserving the code. 9H.5 degrade, 9H.6 full grade suite, chat-route replacement, OPA/Cedar, a second permission store, Alembic, compose changes, Slice 8, Slice 9.

## Capabilities

### New Capabilities

- `ai-harness-policy`: Agent tool ACL aligned with note owner/admin vs member rules, the stable tool error envelope, and the deny-path proof that a forbidden call does not commit.

### Modified Capabilities

- `agent-hitl`: Mutation interrupt still happens before commit, but only after the role is allowed to perform that note action. A forbidden update MUST NOT emit `approval_required` or persist.
- `ai-harness-trust`: Missing harness context still fails closed with no guessed tenant, and the denial the model receives MUST be the 9H.2 `forbidden` envelope.

## Impact

- Code: `src/ai/tools/note_tools.py`, a small envelope helper under `src/ai/harness/`, and `src/notes/service.py` for a workspace-scoped manage/lookup decision that reuses `notes/permissions.py`. Tools still call `NoteService` or `RagService` only. `src/ai/retrieval/filters.py` (`build_rbac_filter`) stays the retrieval mirror for search and summarize; this change does not rewrite Qdrant filters.
- APIs: `/ai/agent*` tool results for failures become a JSON object string. `/ai/chat*` untouched. SSE event types unchanged (`approval_required` keys stay server-authored from 9H.1). No HTTP 500 for a role denial.
- Tenancy: workspace isolation from 9H.1 remains. Role checks are fail-closed. Redis is not a dependency of this slice (budget code only). Postgres and Qdrant writes must not happen on the forbidden path.
- Tests: extend `tests/ai/test_harness_trust.py` and `tests/ai/test_agent_hitl.py` (or a sibling under `tests/ai/`) and keep those suites green. No live model key.
- Blueprint map: **9H.2.1 → 9H.2.2 → 9H.2.3** only (`slice9_policy.md`). Next phase **9H.3** consumes this envelope and these gates; it does not replace them. See design for the sync hint.
