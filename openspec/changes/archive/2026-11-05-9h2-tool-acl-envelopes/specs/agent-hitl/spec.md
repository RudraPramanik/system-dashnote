## MODIFIED Requirements

### Requirement: Mutation tools interrupt before side effects
The agent path MUST pause before `create_note` and `update_note` persist workspace side effects. That pause MUST happen only when the session role is allowed to perform the action under the same owner/admin versus member rules as the notes API. A role denial MUST return a tool failure with code `forbidden`, MUST NOT emit `approval_required`, and MUST NOT persist. Non-mutation tools (e.g. search/summarize) MUST continue without this approval gate. Pending interrupt state MUST use the existing LangGraph checkpointer + `thread_id`; the system MUST NOT require a new `pending_actions` table solely for this gate. When the checkpointer is unavailable, mutation tools MUST still refuse to persist, using the existing blocked-mutation signal rather than a role `forbidden` denial.

#### Scenario: Create note waits for approval
- **GIVEN** an authenticated agent turn whose role is allowed to create a note
- **WHEN** the mutation tool is about to commit via the note service
- **THEN** execution interrupts before the create side effect completes
- **AND** no new note is persisted until an authorized resume approves it

#### Scenario: Search tools are not blocked by HITL
- **GIVEN** an agent turn that only searches or summarizes
- **WHEN** those tools run
- **THEN** they complete without requiring human approval

#### Scenario: Forbidden update does not offer approval
- **GIVEN** a member session
- **AND** a note in that workspace that the notes API would reject for that member to update
- **WHEN** the agent update tool runs
- **THEN** no `approval_required` interrupt is emitted
- **AND** the tool result code is `forbidden`
- **AND** no note content is persisted

#### Scenario: Allowed update still waits for approval
- **GIVEN** an owner or admin session
- **AND** a note in that session workspace
- **WHEN** the agent update tool runs
- **THEN** execution interrupts before the update side effect
- **AND** no note content is persisted until an authorized resume approves it

#### Scenario: Checkpointer block is not a role denial
- **GIVEN** an allowed role
- **AND** the LangGraph checkpointer is not initialized
- **WHEN** create or update is invoked
- **THEN** no note create or update side effect is persisted
- **AND** the client still receives the existing checkpointer / mutation-unavailable signal
- **AND** that signal is not a role `forbidden` envelope
