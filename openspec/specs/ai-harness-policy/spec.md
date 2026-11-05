## Purpose

Makes agent tools obey the same note role rules as the notes API, and returns one stable failure envelope so a forbidden call never commits.

## Requirements

### Requirement: Agent tools enforce note role rules from the session
Search, summarize, create, and update agent tools MUST apply the existing note role rules before they read or write note content: `owner` and `admin` may manage any note in the session workspace; `member` may create notes as the session user, manage only notes they created, and view public notes plus their own private notes. The role MUST come from the trusted harness context for that invoke. The system MUST NOT add a second permission store or policy engine. Workspace id MUST remain the session workspace from harness context. An unknown role MUST be denied and MUST NOT be treated as `member`.

#### Scenario: Member cannot update another user's note
- **GIVEN** a session role of `member` for user U in workspace W
- **AND** a note in W created by a different user
- **WHEN** the update tool is invoked for that note
- **THEN** the tool result is a denial with code `forbidden`
- **AND** no human-approval interrupt is offered
- **AND** the note content is not changed

#### Scenario: Member can still reach approval for their own update
- **GIVEN** a session role of `member` for user U
- **AND** a note in the session workspace created by U
- **WHEN** the update tool is invoked for that note
- **THEN** execution pauses for human approval before any content write
- **AND** the note is not updated until an authorized resume approves it

#### Scenario: Owner create still pauses before commit
- **GIVEN** a session role of `owner` or `admin`
- **WHEN** the create tool is invoked
- **THEN** execution pauses for human approval before any note is persisted
- **AND** no note row is written on the pause itself

#### Scenario: Unknown role is denied
- **GIVEN** a harness role that is not `owner`, `admin`, or `member`
- **WHEN** search, summarize, create, or update runs
- **THEN** the tool result is a denial with code `forbidden`
- **AND** no note is read from another workspace and no note is written

#### Scenario: Summarize uses the same read scope as search
- **GIVEN** a session role of `member`
- **WHEN** the summarize tool runs
- **THEN** retrieval is limited to the same workspace and the same member visibility as search (public notes and the member's own notes)
- **AND** no new role is introduced for summarize

### Requirement: Tool failures share one envelope
When an agent tool fails, the result the model receives MUST be one JSON object serialized as the tool string, with `ok` false, a `code`, and a `message`. Allowed codes are `forbidden`, `not_found`, `budget_exceeded`, `approval_required`, and `upstream`. A successful tool result MUST NOT use that failure shape. `budget_exceeded` MUST be a reserved code only: this phase MUST NOT enforce a Redis AI budget and MUST NOT return `budget_exceeded` from a counter. `approval_required` MUST mean the existing human-approval pause, MUST NOT mean a committed write, and MUST NOT introduce a new server-sent event type. A missing note in the session workspace MUST use `not_found`. An unexpected service failure MUST use `upstream`, and the tool message MUST NOT include a stack trace. Building the envelope MUST NOT itself raise or leave a partial note write. The agent HTTP route MUST NOT turn `forbidden` or `not_found` into an unhandled 500.

#### Scenario: Forbidden and not-found are structured
- **GIVEN** a tool failure that is either a role denial or a missing note in the session workspace
- **WHEN** the model receives the tool result
- **THEN** the result parses as JSON with `ok` false and code `forbidden` or `not_found`
- **AND** the message is plain text without a stack trace

#### Scenario: Service error becomes upstream
- **GIVEN** NoteService or RagService raises an unexpected error during an allowed tool call
- **WHEN** the tool handles that error
- **THEN** the model receives code `upstream`
- **AND** the tool message does not contain a stack trace
- **AND** no partial note write is kept as success

#### Scenario: Budget code is unused
- **GIVEN** this phase is in effect
- **WHEN** an agent tool runs under the normal budget-free path
- **THEN** the tool does not return `budget_exceeded`
- **AND** no Redis AI budget key is required for the call to proceed

### Requirement: A forbidden tool call does not commit
A tool decision of `forbidden` MUST stop the tool. It MUST NOT fall through into a note create or update, and MUST NOT write a note row or a note vector. Human approval MUST NOT complete a write after that decision. The repository MUST include an automated test of this deny path that runs without a live model provider key. A failing assertion MUST fail the test run.

#### Scenario: Denied update writes nothing
- **GIVEN** a role the notes API would reject for that update
- **WHEN** the update tool runs
- **THEN** the result code is `forbidden`
- **AND** no note create or update commit runs
- **AND** no note vector write runs

#### Scenario: Deny-path test needs no live model
- **GIVEN** the deny-path test or fixture
- **WHEN** pull-request CI runs without a live LLM key
- **THEN** the case executes
- **AND** it fails if a note commit happens after `forbidden`

### Requirement: Chat path stays a separate surface
Tool ACL and error envelopes in this phase MUST apply to `/ai/agent*` tools. `/ai/chat` and `/ai/chat/stream` MUST remain the fast RAG path and MUST NOT be replaced by the agent. Local full-stack compose services MUST keep working. Direct note REST behavior MUST stay the source of the role rules and MUST NOT start requiring the agent checkpointer.

#### Scenario: Chat is unchanged
- **GIVEN** agent tools enforce role rules and failure envelopes
- **WHEN** a client calls `/ai/chat` or `/ai/chat/stream`
- **THEN** RAG chat still runs on its existing path
- **AND** agent routes remain separately addressable
