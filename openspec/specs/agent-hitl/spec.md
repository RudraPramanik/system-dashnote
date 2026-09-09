## Purpose

API-first human-in-the-loop for DashNote agent note mutations: interrupt before create/update side effects, stream an approval event, and resume or reject with workspace ownership checks—without requiring a polished frontend console.

## Requirements

### Requirement: Mutation tools interrupt before side effects
The agent path MUST pause before `create_note` and `update_note` persist workspace side effects. Non-mutation tools (e.g. search/summarize) MUST continue without this approval gate. Pending interrupt state MUST use the existing LangGraph checkpointer + `thread_id`; the system MUST NOT require a new `pending_actions` table solely for this gate.

#### Scenario: Create note waits for approval
- **GIVEN** an authenticated agent turn that would create a note
- **WHEN** the mutation tool is about to commit via the note service
- **THEN** execution interrupts before the create side effect completes
- **AND** no new note is persisted until an authorized resume approves it

#### Scenario: Search tools are not blocked by HITL
- **GIVEN** an agent turn that only searches or summarizes
- **WHEN** those tools run
- **THEN** they complete without requiring human approval

### Requirement: Stream emits approval_required then closes
When a mutation interrupt occurs on the streaming agent surface, the API MUST emit an SSE event with type `approval_required` including at least `tool`, `args` (or documented args summary), `thread_id`, and `interrupt_id`. After emitting `approval_required`, the stream MUST end (client reconnects via resume/reject). Existing event types (`token`, `tool_start`, `tool_end`, `done`, `error`) MUST remain valid.

#### Scenario: Client can parse interrupt and reconnect
- **GIVEN** a streaming agent request that triggers a mutation interrupt
- **WHEN** the client reads SSE events
- **THEN** it receives `approval_required` with the locked fields
- **AND** the stream ends so the client uses the resume or reject API with the same `thread_id`

### Requirement: Resume and reject enforce workspace ownership
The system MUST expose authenticated approve (resume) and reject operations for a pending agent interrupt. Both MUST re-validate that the `thread_id` / checkpoint belongs to the caller’s workspace from JWT/`RequestContext` before any further mutation. Arbitrary or cross-workspace `thread_id` values MUST be denied with no mutation side effect. Reject MUST end the turn without applying the pending create/update.

#### Scenario: Same-workspace approve completes mutation
- **GIVEN** a pending interrupt for thread T owned by workspace W
- **AND** the caller is authenticated for workspace W
- **WHEN** they approve/resume with thread T
- **THEN** the pending mutation may complete through the note service layer

#### Scenario: Cross-workspace resume is denied
- **GIVEN** a pending interrupt for workspace W
- **WHEN** a caller authenticated for a different workspace attempts resume or reject with that `thread_id`
- **THEN** the request is denied
- **AND** no note create/update side effect occurs

#### Scenario: Reject prevents side effect
- **GIVEN** a pending create or update interrupt
- **WHEN** the owning caller rejects
- **THEN** the mutation does not persist
- **AND** the agent turn ends without applying the tool side effect

### Requirement: Chat path and tenant freeze remain intact
HITL MUST apply only to `/ai/agent*` mutation paths. `/ai/chat*` MUST remain a separate fast RAG surface and MUST NOT be converted into the agent. Workspace, user, and role for tools and resume MUST come from trusted request/graph state—not from model-overridable tenant fields. Tools MUST continue to call service-layer APIs (e.g. `NoteService`), not repositories directly.

#### Scenario: Chat coexistence after HITL
- **GIVEN** HITL is enabled on the agent
- **WHEN** a client calls `/ai/chat` or `/ai/chat/stream`
- **THEN** RAG chat behaves without requiring mutation approval
- **AND** agent routes remain separately addressable

### Requirement: HITL is verifiable by script and automated tests
The repository MUST provide script/curl (or equivalent) verification and automated tests covering at least: interrupt before mutation, approve path, reject path, and cross-workspace resume denial. Those API-first tests MUST still pass without a Next.js console. A dedicated automation-inbox UI MUST NOT be required. The product agent view (sibling DashNotes, documented in `frontendguide.md`) MUST still implement in-thread Approve/Reject as specified in this capability so a user can finish `create_note` / `update_note` without curl.

#### Scenario: Operator proves approve vs reject without FE console
- **GIVEN** local API is running with HITL enabled
- **WHEN** an operator runs the documented script/tests
- **THEN** they can demonstrate approval completes a mutation and reject does not
- **AND** that script success does not depend on a Next.js approval console

#### Scenario: Product UI is documented as required for the user path
- **GIVEN** a user is in the DashNotes agent view
- **WHEN** the agent pauses on `create_note` or `update_note`
- **THEN** the documented client contract MUST include in-thread Approve and Reject
- **AND** MUST NOT treat curl as the only way a product user can finish the mutation

### Requirement: Product agent UI completes HITL in the same thread
The DashNotes agent view MUST handle SSE `type: "approval_required"` (fields `tool`, `args`, `thread_id`, `interrupt_id`) after the stream ends. The UI MUST show the pending mutation (at least tool name and title/content summary from `args`) and MUST offer Approve and Reject actions. Approve MUST call `POST /ai/agent/resume` with the same `thread_id` (and `interrupt_id` when present) using the existing Bearer JWT. Reject MUST call `POST /ai/agent/reject` the same way. The client MUST NOT send `workspace_id`, `user_id`, or `role` on those bodies. The client MUST NOT auto-approve. Search and summarize MUST still run without this UI.

#### Scenario: User approves a pending create note
- **GIVEN** an authenticated agent stream emitted `approval_required` for `create_note`
- **AND** the stream has ended
- **WHEN** the same user clicks Approve in the agent thread
- **THEN** the client MUST POST to `/ai/agent/resume` with that `thread_id`
- **AND** MUST NOT include a client-chosen workspace override
- **AND** on success the UI MUST leave the stuck "Creating note…" running state

#### Scenario: User rejects a pending mutation
- **GIVEN** a pending `create_note` or `update_note` interrupt in the agent thread
- **WHEN** the user clicks Reject
- **THEN** the client MUST POST to `/ai/agent/reject` with that `thread_id`
- **AND** no note create/update MUST persist as a result of that reject

#### Scenario: Search still has no approval card
- **GIVEN** an agent turn that only searches or summarizes
- **WHEN** those tools complete
- **THEN** the UI MUST NOT require Approve or Reject for that turn
