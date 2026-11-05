## ADDED Requirements

### Requirement: Untrusted text cannot skip human approval
Retrieved note or file text, and tool output fed back to the model, that tells the model to skip approval or write immediately MUST NOT cause `create_note` or `update_note` to persist without the existing human-approval interrupt. When the session role is allowed to perform that action, execution MUST still pause before the write. When the notes API would reject that role for the note, the tool MUST still return `forbidden`, MUST NOT emit `approval_required`, and MUST NOT persist. Delimiters and prompt text MUST NOT replace this gate.

#### Scenario: Skip-approval text still interrupts an allowed write
- **GIVEN** a session role allowed to create or update a note
- **AND** retrieved or tool text that says to skip approval and write the note
- **WHEN** the mutation tool runs
- **THEN** execution pauses for human approval before any content write
- **AND** no note is persisted on that pause

#### Scenario: Skip-approval text does not override a role denial
- **GIVEN** a member session
- **AND** a note in that workspace that the notes API would reject for that member to update
- **AND** text that says to skip approval and write that note
- **WHEN** the update tool runs
- **THEN** no `approval_required` interrupt is emitted
- **AND** the tool result code is `forbidden`
- **AND** no note content is persisted
