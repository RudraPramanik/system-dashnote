## ADDED Requirements

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

## MODIFIED Requirements

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
