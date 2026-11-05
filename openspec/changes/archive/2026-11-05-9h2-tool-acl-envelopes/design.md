## Context

See proposal.md for why. 9H.1 already freezes tenant on `HarnessContext` and omits tenant fields from tool schemas (`src/ai/harness/context.py`, `src/ai/tools/note_tools.py`). Mutation tools interrupt before `NoteService.create_note` / `update_note`. Role rules live in `src/notes/permissions.py` and are applied on `src/notes/router.py` (`PATCH` uses `can_manage_note`: owner/admin any note, member only `created_by`). `NoteService.update_note` only checks the note is in the workspace. Search already passes `role` into `RagService` → `build_rbac_filter()` (`src/ai/retrieval/filters.py`), and that filter treats every non-owner/admin role as a member. `note_tools.py` may call `NoteService` or `RagService` only, and must not import `RequestContext`.

Requirements live in `specs/ai-harness-policy/spec.md`, `specs/agent-hitl/spec.md`, and `specs/ai-harness-trust/spec.md`.

This work runs in the API process, inside the LangGraph tool node. It does not run on the ARQ worker. No Qdrant collection change (`notes_chunks` / `files_chunks` stay as they are). No Alembic, settings, or compose change.

## Goals / Non-Goals

**Goals:**

- One allow-list (`owner` | `admin` | `member`) in front of every agent tool, then the same manage/view rules as the notes API.
- One JSON failure string for the model. HITL pause stays the existing SSE `approval_required` event.
- A pytest deny path with no live LLM key, plus the existing harness-trust and HITL suites still green.

**Non-Goals:**

- Implementing 9H.3, 9H.4 counters, 9H.5, or 9H.6. The 9H.3 sync contract below is a constraint for the next change, not work in this one.
- Rewriting `build_rbac_filter`, chat prompts, or REST status codes.
- OPA, Cedar, a new role table, or moving RBAC into the tool file by copying `can_manage_note`.

## Decisions

### 1. Role gate in the tool, rule evaluation in NoteService

**Choice:** `note_tools` checks the harness role against `{owner, admin, member}` and, on update, asks `NoteService` for a workspace-scoped decision before `interrupt()`. `NoteService` builds a `RequestContext` and calls `can_manage_note` / a not-found result. The tool never imports `notes.permissions` or `RequestContext`.

**Why:** `src/ai/*` cannot own the REST rule, and the tool import law forbids `RequestContext`. `can_manage_note` alone treats an unknown role like a member (own-note manage). The allow-list must run first, in both the tool and `NoteService`, so an unknown role cannot manage their own note.

**Alternatives:** Duplicate the three-line rule inside `ai/` (second permission product — rejected). Import `notes.permissions` from the tool (breaks the tool import law — rejected). Change `build_rbac_filter` to fail closed (retrieval behavior change beyond this slice — rejected). Unknown roles are stopped before `RagService`, so the filter never sees them.

### 2. Update and create sequences

```
HarnessContext
    │
    ├─ missing ──────────────► forbidden envelope, no service call
    ├─ role not in allow-list ► forbidden envelope, no service call
    │
    ├─ search / summarize ───► RagService.answer(session workspace, user, role)
    │                          summarize uses the same call shape as search
    │
    ├─ create (allowed role)
    │     checkpointer missing → existing blocked-mutation signal (not forbidden)
    │     else interrupt (server-authored tenant args) → on approve NoteService.create_note
    │
    └─ update (allowed role)
          checkpointer missing → existing blocked-mutation signal
          NoteService decision (workspace get, no save):
              missing note → not_found, no interrupt
              !can_manage  → forbidden, no interrupt, no save
              allowed      → interrupt → on approve update_note
                           → update_note re-checks can_manage; denial → forbidden, no save
```

Create stays “any allowed role creates as the session user”, matching `POST /notes/` (no extra owner check). Member update of someone else’s note, including a public note they do not own, is `forbidden` (REST returns 403, not 404). Another workspace’s id is `not_found` because the repository is workspace-scoped. Do not query a second workspace.

User reject keeps today’s plain non-commit strings. Do not relabel reject as `forbidden`.

### 3. Envelope helper

**Choice:** `ai/harness/errors.py` (name flexible) with a closed code set and one function that always returns a string:

`{"ok": false, "code": "<code>", "message": "<fixed text>"}`

On any serialization failure, return a hardcoded `upstream` string. Never raise. Log unexpected exceptions server-side; do not put `traceback` or `str(exc)` in `message`.

Map typed note outcomes (`not found`, `access denied`) to `not_found` and `forbidden`. Map anything else from an allowed call to `upstream`. Missing harness context uses this helper with `forbidden` (replaces the 9H.1 plain deny string).

`budget_exceeded` and `approval_required` are constants in that module. Nothing in this change returns `budget_exceeded`. `approval_required` is not a tool return that replaces SSE; the interrupt payload in `ai/hitl.py` stays the pause signal, with tenant fields still copied from `HarnessContext`.

Success strings (`Note created successfully…`, search answers) stay prose.

**Why:** The tool node returns strings today. One JSON object is the blueprint fallback and needs no new SSE type.

**Alternatives:** New streaming event for errors (explicitly out of 9H.2.2 — rejected). Plain-text prefix only (harder for 9H.6 and 9H.4 to share — rejected).

### 4. Where writes are allowed to happen

Only `NoteService.create_note` and `NoteService.update_note` after an approved interrupt. The pre-HITL update decision is a read through `NoteService` (repository get inside the service). Tools still must not call repositories or `NoteVectorIndexer`. Agent note writes today do not enqueue embeddings inside `NoteService`; do not add that enqueue here. The deny-path test fails if `create_note` / `update_note` runs after `forbidden`, which is the commit this phase can actually perform.

### 5. Sync contract for 9H.3 (do not implement it here)

9H.3 (`slice9_policy.md` substages 9H.3.1–9H.3.3) should sit on top of this phase:

| This phase leaves | 9H.3 should do | 9H.3 must not do |
|-------------------|----------------|------------------|
| Raw tool returns: prose on success, JSON envelope on failure | Wrap text that re-enters the model (retrieved chunks and tool strings) in start/end markers, outside the JSON object so `code` stays intact | Parse the envelope to decide allow/deny, or drop ACL because the prompt says content is data |
| Allow-list + `can_manage_note` before interrupt | Poisoned-note fixtures call the same tool entry points: “switch workspace” still uses session tenant or `forbidden`; “skip approval” still interrupts when the role is allowed, and still does not interrupt when it is not | A second policy check or a path that commits without HITL |
| `tool_error()` as the only failure shape | Put the delimiter helper in `ai` or `shared`, imported by RAG context building and by the message boundary. If import laws block one helper, duplicate the few wrap lines. Do not import routers | Langfuse SDK inside `src/ai/*`, a moderation vendor, or PII redaction |
| Tests assert the raw envelope from the tool return | Prefer wrapping where the model message is built, not inside the deny return, so these tests keep parsing JSON. If the wrap has to live in the tool, markers go around the whole string and `tool_error()` stays the unwrapped builder | Rewriting envelopes into a new schema |

9H.4 later returns `budget_exceeded` from this same helper. It does not get a second JSON shape. Redis fail-open stays a 9H.4 rule.

### 6. Tests prove the slice without a hosted model

Add `tests/ai/test_harness_policy.py`. Drive tool coroutines with a set `HarnessContext` and a fake `NoteService` / `RagService` (same style as `tests/ai/test_harness_trust.py`). Cover: member forbidden update (no interrupt, no `update_note`), owner update still interrupts, missing note `not_found`, unknown role does not call RAG or create, service exception `upstream` without a stack trace, missing context `forbidden` envelope. Re-run `tests/ai/test_harness_trust.py` and `tests/ai/test_agent_hitl.py` and update only assertions that still expect the old plain missing-context string. No live LLM key. Do not weaken member rules to go green. Do not edit `/ai/chat*` handlers.

Name `test_forbidden_update_does_not_commit` (or the final test name) in the apply summary so 9H.6 can point at it.

## Risks / Trade-offs

- [Allow-list and `can_manage_note` disagree] → Unknown roles die on the allow-list; manage checks only run for the three known roles. Add a unit test that an unknown role never reaches `can_manage_note` success.
- [Pre-check then approve races a role or owner change] → `update_note` re-checks before save; failure becomes `forbidden` and does not save.
- [JSON tool strings confuse the model vs prose success] → Accepted; 9H.3 wraps both as data. Keep success prose so current HITL success tests stay meaningful.
- [Checkpointer failure gets mis-labeled `forbidden`] → Leave the existing blocked-mutation return in place and test it is not the role envelope.
- [`build_rbac_filter` still treats garbage roles as members if called directly] → Agent tools never call it with a garbage role. A filter change is out of scope; comment the allow-list as the agent fail-closed gate.
- [Scope creep into delimiters] → 9H.3 table is a contract only. No marker helper in this change.

## Migration Plan

1. Land the envelope helper and point the missing-context deny at `forbidden`.
2. Land `NoteService` decision + update re-check, then wire create/update/search/summarize gates. Chat routes and REST routers stay behaviorally the same.
3. Add deny-path tests; run the three AI test modules above.
4. Rollback is reverting the change. No migration, no feature flag, no Redis key.

## Open Questions

None that change the specs or the task split. Module file names inside `ai/harness/` may follow whatever layout apply finds next to `context.py`.
