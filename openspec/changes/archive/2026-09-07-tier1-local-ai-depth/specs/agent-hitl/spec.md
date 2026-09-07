## Purpose

API-first human-in-the-loop for DashNote agent note mutations: interrupt before create/update side effects, stream an approval event, and resume or reject with workspace ownership checks—without requiring a polished frontend console.

## ADDED Requirements

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
The repository MUST provide script/curl (or equivalent) verification and automated tests covering at least: interrupt before mutation, approve path, reject path, and cross-workspace resume denial. A polished Next.js approval UI MUST NOT be required to pass this capability’s gate.

#### Scenario: Operator proves approve vs reject without FE console
- **GIVEN** local API is running with HITL enabled
- **WHEN** an operator runs the documented script/tests
- **THEN** they can demonstrate approval completes a mutation and reject does not
- **AND** success does not depend on a Next.js approval console
