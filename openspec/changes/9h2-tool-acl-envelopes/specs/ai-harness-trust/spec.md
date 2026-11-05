## MODIFIED Requirements

### Requirement: Missing harness context fails closed
If trusted harness context is missing at tool execution time, the tool MUST deny the call. The denial the model receives MUST be the tool error envelope with code `forbidden`. The system MUST NOT default, guess, or parse a workspace id from the user message. The system MUST NOT call NoteService or RagService with a guessed tenant.

#### Scenario: Tool without context is denied
- **GIVEN** a tool execution path with no harness context available
- **WHEN** search, create, update, or summarize would call a service
- **THEN** the tool returns a denial whose code is `forbidden`
- **AND** no NoteService or RagService call is made with a guessed tenant
- **AND** the denial does not include a stack trace
