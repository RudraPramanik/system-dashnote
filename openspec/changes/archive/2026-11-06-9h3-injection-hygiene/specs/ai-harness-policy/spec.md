## MODIFIED Requirements

### Requirement: Tool failures share one envelope
When an agent tool fails, the tool return MUST be one JSON object serialized as the tool string, with `ok` false, a `code`, and a `message`. Allowed codes are `forbidden`, `not_found`, `budget_exceeded`, `approval_required`, and `upstream`. A successful tool result MUST NOT use that failure shape. `budget_exceeded` MUST be a reserved code only: this capability MUST NOT enforce a Redis AI budget and MUST NOT return `budget_exceeded` from a counter. `approval_required` MUST mean the existing human-approval pause, MUST NOT mean a committed write, and MUST NOT introduce a new server-sent event type. A missing note in the session workspace MUST use `not_found`. An unexpected service failure MUST use `upstream`, and the tool message MUST NOT include a stack trace. Building the envelope MUST NOT itself raise or leave a partial note write. The agent HTTP route MUST NOT turn `forbidden` or `not_found` into an unhandled 500. The tool return that callers read before a model message is built MUST stay that raw JSON string. When that string is placed into a model message, it MUST be wrapped as untrusted data and the same JSON object MUST remain intact inside the markers so `code` is still readable. Wrapping MUST NOT decide allow or deny, MUST NOT change the code, and MUST NOT perform a note write.

#### Scenario: Forbidden and not-found are structured
- **GIVEN** a tool failure that is either a role denial or a missing note in the session workspace
- **WHEN** the tool returns its result, before that string is placed in a model message
- **THEN** the result parses as JSON with `ok` false and code `forbidden` or `not_found`
- **AND** the message is plain text without a stack trace
- **AND** when that same string is placed in a model message, the JSON object remains intact inside the data markers

#### Scenario: Service error becomes upstream
- **GIVEN** NoteService or RagService raises an unexpected error during an allowed tool call
- **WHEN** the tool handles that error
- **THEN** the model-facing path still carries code `upstream`
- **AND** the tool message does not contain a stack trace
- **AND** no partial note write is kept as success

#### Scenario: Budget code is unused
- **GIVEN** this capability is in effect
- **WHEN** an agent tool runs under the normal budget-free path
- **THEN** the tool does not return `budget_exceeded`
- **AND** no Redis AI budget key is required for the call to proceed

#### Scenario: Wrapping a denial does not authorize it
- **GIVEN** a tool return with code `forbidden`
- **WHEN** a model message is built around that return
- **THEN** the code inside the markers is still `forbidden`
- **AND** no note create or update runs as part of wrapping
