# Slice 9H.1 — Trusted Tenant Bind
## Composer substages (inventory → bind → HITL payload → golden theme)

> **Parent index (order source):** [`slice9_H.md`](slice9_H.md) — phase **9H.1**, calendar position 1st.  
> **Operator default:** [`../blueprint9.md`](../blueprint9.md).  
> **Code anchors (read, do not expand scope):** `src/ai/tools/schemas.py` · `src/ai/tools/note_tools.py` · `src/ai/workflows/workspace_assistant.py` · `src/ai_routes/agent.py`  
> **Goal:** Agent tools use workspace, user, and role from HarnessContext. The model cannot choose a tenant.  
> **This file is a prompt blueprint.** Implementing the code is a later apply of these substages.

Order reminder (not a prerequisite chain for other phases): 9H.1 → 9H.2 → 9H.3 → 9H.4 → 9H.5 → 9H.6. Do not implement 9H.2+ here.

---

## Sub-step 9H.1.1 — Inventory

**Goal:** Record where tool schemas and the system prompt still ask the model to pass `workspace_id`, `user_id`, and `role`.

**Fallback:** If a field is injected only in the prompt and not in the schema, list it anyway. Do not delete fields in this substep.

**Error boundary:** Inventory mistakes are documentation errors. Do not change runtime behavior in this substep, so there is no new failure mode.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.1.1 — Inventory model-supplied tenant fields.

Paste ARCHITECTURE LAW — Slice 9H first.

GOAL:
  List every tool argument and prompt sentence that tells the model to supply
  workspace_id, user_id, or role. Name the file. Do not change behavior yet.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Tools call NoteService or RagService only.

VALIDATION GATE:
  A short inventory table exists in the session notes or a doc comment the
  operator asked for, covering search, create, update, and summarize tools.
  No service call site was switched to a different tenant source in this substep.

FALLBACK:
  If a tenant field is prompt-only, record it as prompt-only. Do not invent a schema change yet.

ERROR BOUNDARY:
  No runtime change. If you are unsure whether a field is tenant identity, list it
  under "needs review" instead of deleting it.
```

---

## Sub-step 9H.1.2 — Bind or overwrite

**Goal:** Tool execution uses HarnessContext for tenant fields. Business args (query, title, content, note id) stay model-owned.

**Preferred:** Remove `workspace_id`, `user_id`, and `role` from tool argument schemas.  
**Fallback:** If the installed tool API requires those schema fields, overwrite them from HarnessContext immediately before `NoteService` / `RagService`. Never persist the model values. Log when the model value differed.

**Error boundary:** Missing HarnessContext denies the tool (`forbidden` or the closest existing deny string this substep can return without inventing 9H.2’s full envelope). Never call another workspace.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.1.2 — Bind tenant from HarnessContext.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.1.1 inventory.

GOAL:
  Build HarnessContext from the authenticated request (workspace_id, user_id, role)
  and the graph state for this invoke. Tool wrappers read tenant fields only from it.
  Prefer dropping those fields from tool schemas. Business arguments stay model-owned.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Tools call NoteService or RagService only. Never repositories.
  Model-supplied workspace_id, user_id, and role MUST NOT be the values passed to services.

VALIDATION GATE:
  A unit test shows a fake tool call whose workspace_id differs from session state
  still queries or mutates only the session workspace (or is denied).
  Chat routes are untouched.

FALLBACK:
  If schemas must still expose tenant fields, overwrite them from HarnessContext
  before the service call, ignore model values, and log the mismatch.

ERROR BOUNDARY:
  Missing HarnessContext → deny the tool. Do not default, guess, or read a workspace
  id out of the user message. Fail closed.
```

---

## Sub-step 9H.1.3 — HITL payload uses bound identity

**Goal:** Approval payloads and resume checks show the bound workspace, user, and role, not whatever the model echoed.

**Fallback:** If the SSE `approval_required.args` shape must stay stable for the current UI, put the bound ids in that object and document that they are server-authored.

**Error boundary:** Resume of a thread whose checkpoint workspace does not match the caller still returns 403. Do not widen resume to accept a model-chosen workspace.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.1.3 — HITL payloads carry bound tenant identity only.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.1.2 bind or overwrite is in place.

GOAL:
  create_note and update_note still interrupt before commit.
  The approval payload's workspace_id, user_id, and role are copied from HarnessContext
  after binding, never from raw model JSON.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT remove HITL. Do NOT add a second pending-actions table.

VALIDATION GATE:
  Existing HITL smoke or tests still pass.
  An approval payload fixture shows tenant fields equal to the session, even if the
  model arguments differed before overwrite.

FALLBACK:
  Keep the current approval_required JSON keys. Fill tenant fields from HarnessContext
  and document them as server-authored.

ERROR BOUNDARY:
  Resume/reject still rejects a thread_id whose checkpoint workspace is not the
  caller's. Fail closed with the existing 403 behavior. No cross-workspace resume.
```

---

## Sub-step 9H.1.4 — Invented-workspace golden theme

**Goal:** Specify (and add, when this substep is implemented) a fixture case: the model invents another workspace id and the tool does not use it.

**Fallback:** If the live agent eval runner cannot load the case without an API key, keep the case in the fixture corpus only. Do not require a live LLM in CI.

**Error boundary:** A failing golden fails the fixture run. It must not be skipped to keep CI green.

```
ROLE: Senior AI systems engineer.

OBJECTIVE: Slice 9H.1.4 — Fixture theme for a model-invented workspace id.

Paste ARCHITECTURE LAW — Slice 9H first.
Prerequisite: 9H.1.2 behavior exists to assert against.

GOAL:
  Add a fixture golden: tool arguments contain a workspace_id that is not the session
  workspace. Expected result: the service is called with the session workspace, or the
  tool is denied. The other workspace's notes are not read or written.

CONSTRAINTS:
  Do NOT replace /ai/chat* with /ai/agent*. Both routes remain.
  Do NOT break local docker compose (docker-compose.yml full stack: db, redis, qdrant, api, worker, nginx, prometheus).
  Do NOT implement a later 9H phase in this session.
  Do NOT require a live LLM key for this fixture to pass in CI.

VALIDATION GATE:
  The fixture runs without network calls to a model provider and fails if the
  foreign workspace id is the one passed into NoteService or RagService.

FALLBACK:
  If the trajectory runner cannot express this yet, add a focused unit test with the
  same assertion and point the blueprint note at that test. Do not drop the theme.

ERROR BOUNDARY:
  Assertion failure is a red test. Do not catch it and continue the turn against
  the foreign workspace.
```
