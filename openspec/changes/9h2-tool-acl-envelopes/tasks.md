## 1. Error envelope (9H.2.2 contract)

- [x] 1.1 Add a tool-error helper under `src/ai/harness/` that always returns a JSON string `{"ok": false, "code", "message"}` for codes `forbidden`, `not_found`, `budget_exceeded`, `approval_required`, and `upstream`, and returns a hardcoded `upstream` string if serialization fails
- [x] 1.2 Keep `budget_exceeded` and `approval_required` as reserved constants only: no Redis budget check, and no new SSE event type
- [x] 1.3 Point the missing-`HarnessContext` deny in `src/ai/tools/note_tools.py` at the `forbidden` envelope (no guessed workspace, no stack trace)

## 2. NoteService role decision (API service path)

- [x] 2.1 Add a workspace-scoped update decision on `NoteService` that reads the note in the session workspace, returns not-found when absent, and calls `can_manage_note` for `owner` / `admin` / `member` only
- [x] 2.2 Reject an unknown role inside that decision before `can_manage_note` can treat it as a member
- [x] 2.3 Re-check `can_manage_note` inside `update_note` before save, and surface a typed denial the tool can map without parsing exception text
- [x] 2.4 Leave the ARQ worker, Qdrant indexers, Alembic, settings, and `docker-compose.yml` unchanged

## 3. Tool ACL (9H.2.1)

- [x] 3.1 In search, summarize, create, and update, deny with `forbidden` when harness role is not `owner`, `admin`, or `member`, and do not call `RagService` or a mutating `NoteService` method
- [x] 3.2 On update, run the NoteService decision before `interrupt()`: `not_found` or `forbidden` returns that envelope and does not pause for approval or save
- [x] 3.3 When the role is allowed, keep create and update interrupting before commit with server-authored tenant args; member create stays allowed as the session user
- [x] 3.4 Keep the existing checkpointer-unavailable signal for allowed mutations; do not relabel it as role `forbidden`
- [x] 3.5 Keep user-reject as a non-commit result that is not `forbidden`; summarize keeps using the same `RagService.answer` role scope as search
- [x] 3.6 Do not import `RequestContext` or `notes.permissions` from `src/ai/tools/note_tools.py`, and do not edit `/ai/chat*` handlers

## 4. Failure mapping (9H.2.2 on the tool path)

- [x] 4.1 Map note not-found and access-denied outcomes to `not_found` and `forbidden` envelopes; map unexpected service errors to `upstream` with a fixed message and a server-side log
- [x] 4.2 Leave successful tool results as the current prose (or RAG answer), not the failure JSON shape

## 5. Proof and regression (9H.2.3)

- [x] 5.1 Add `tests/ai/test_harness_policy.py` with `test_forbidden_update_does_not_commit`: a member update the notes API would reject returns `forbidden`, does not interrupt, and does not call `NoteService.update_note`
- [x] 5.2 In that module, cover owner/admin update still interrupts without a silent commit, missing note `not_found`, unknown role does not call RAG or create, service exception `upstream` without a stack trace, and missing harness context `forbidden`
- [x] 5.3 Update `tests/ai/test_harness_trust.py` only where it still expects the pre-envelope missing-context string
- [x] 5.4 Run `python -m pytest tests/ai/test_harness_policy.py tests/ai/test_harness_trust.py tests/ai/test_agent_hitl.py -q` with no live LLM key and fix regressions without weakening member rules
- [x] 5.5 Record the deny-path test name in the apply summary so 9H.6 can point at it; do not add 9H.3 delimiter, prompt, or poisoned-note code in this change
