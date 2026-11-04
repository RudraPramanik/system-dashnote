## ADDED Requirements

### Requirement: Approval payloads carry server-bound tenant identity
When `create_note` or `update_note` interrupts for human approval, the `approval_required` SSE (or equivalent sync) payload’s tenant fields (`workspace_id`, `user_id`, `role` when present in `args`) MUST be copied from the trusted harness context after bind, never from raw model tool JSON. Existing approval keys MAY stay stable for the product UI; those tenant values MUST be documented as server-authored. Resume and reject MUST continue to deny a `thread_id` whose checkpoint workspace is not the caller’s (fail closed, existing 403 behavior). HITL MUST still interrupt before any create/update commit.

#### Scenario: Approval args match session even if model differed
- **GIVEN** a mutation tool call where the model supplied a different workspace id than the session
- **AND** harness bind or overwrite has already applied
- **WHEN** the agent emits `approval_required`
- **THEN** tenant fields in the approval payload equal the session harness context
- **AND** they do not equal the foreign model-supplied workspace id

#### Scenario: Cross-workspace resume still denied
- **GIVEN** a pending interrupt whose checkpoint belongs to workspace W
- **WHEN** a caller authenticated for a different workspace attempts resume or reject
- **THEN** the request is denied with existing fail-closed behavior
- **AND** no note create/update side effect occurs
