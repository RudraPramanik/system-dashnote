## Purpose

Treats retrieved note and file text, and tool output fed back to the model, as untrusted data so it cannot retarget the session or skip human approval.

## Requirements

### Requirement: Retrieved chunks and tool outputs are delimited as data
Note chunks and file chunks placed into a model prompt, and tool strings placed back into a model message, MUST be wrapped with a start marker and a matching end marker. When a stable id exists, the markers MUST include it. System instructions MUST stay outside the markers. The user's question MAY stay outside the chunk markers. If the payload contains the marker strings, the wrapper MUST still close on its own end marker and MUST NOT leave the chunk open. If wrapping one chunk fails, that chunk MUST be omitted and the remaining chunks MUST still be wrapped and sent. Raw chunk text MUST NOT be written into a system-role message. This change MUST NOT add a third-party moderation vendor or an automated PII redaction pipeline.

#### Scenario: A chunk that contains the markers still closes
- **GIVEN** a retrieved note or file chunk whose text contains the start marker and the end marker
- **WHEN** the RAG context message is built
- **THEN** that chunk is closed by the wrapper's own end marker
- **AND** the system-role message is the system instruction
- **AND** the system-role message is not the chunk text

#### Scenario: A wrap failure drops only that chunk
- **GIVEN** more than one retrieved chunk
- **AND** wrapping fails for one of them
- **WHEN** the context message is built
- **THEN** the failing chunk's raw text is absent from the system role and from the user message
- **AND** each remaining chunk is present inside start and end markers

#### Scenario: A tool string re-enters the model as data
- **GIVEN** a tool return that is either success text or a failure envelope
- **WHEN** that string is placed into a model tool message
- **THEN** it sits inside a start marker and a matching end marker
- **AND** a failure envelope's JSON object is unchanged inside those markers

### Requirement: Prompts treat delimited content as data
The RAG system prompt and the workspace assistant prompt MUST each state that content inside the data delimiters is untrusted notes or tool output, not instructions. Each prompt MUST say that this content cannot change workspace, user, or role, cannot skip approval, and cannot override tool policy. Both prompts MUST name the same delimiter. The system MUST NOT introduce a new product persona. On the chat path, citation grounding MUST remain: each retrieved chunk id MUST still appear in a `[CHUNK:{id}]` tag, the system prompt MUST still tell the model to cite those ids, and the existing insufficient-context refusal that mentions notes and files MUST remain. The prompt text MUST NOT replace session tenant binding or note role checks.

#### Scenario: Both prompts carry the same data rule
- **GIVEN** the RAG system prompt and the workspace assistant prompt
- **WHEN** those prompts are read
- **THEN** each contains the data-not-instructions rule
- **AND** each names the delimiter
- **AND** neither prompt is a new assistant persona

#### Scenario: Chat citation grounding stays
- **GIVEN** a retrieved chunk with an id
- **WHEN** the RAG user message and system prompt are built
- **THEN** the user message contains that id in a `[CHUNK:{id}]` tag inside the data markers
- **AND** the system prompt still instructs the model to cite those ids
- **AND** the system prompt still contains the notes-and-files refusal

### Requirement: Poisoned content cannot retarget the session or skip approval
The repository MUST include two automated fixtures that run without a live model provider key. One fixture MUST cover retrieved or tool text that tells the model to use another workspace id. The other MUST cover text that tells the model to skip approval and write a note. A foreign workspace MUST NOT be queried. A note MUST NOT be committed without the existing human-approval interrupt. A failing assertion MUST fail the test run. Neither fixture MUST be skipped. A check that needs a hosted model MUST NOT replace these fixtures.

#### Scenario: Foreign workspace text does not change the session
- **GIVEN** a session bound to workspace W
- **AND** retrieved or tool text that names a different workspace id
- **WHEN** search, summarize, create, or update runs for that session
- **THEN** the note or retrieval service is called only with W, or the tool is denied
- **AND** the foreign workspace is not queried
- **AND** the fixture fails if the foreign workspace id is the one used

#### Scenario: Skip-approval text does not commit
- **GIVEN** text that says to skip approval and write the note
- **AND** a session role allowed to create or update
- **WHEN** the mutation tool runs
- **THEN** no note is committed before human approval
- **AND** the fixture fails if a commit happens without that approval

#### Scenario: Both fixtures run without a live model
- **GIVEN** the two poisoned-content fixtures
- **WHEN** pull-request CI runs without a live LLM key
- **THEN** both fixtures execute
- **AND** neither is skipped

### Requirement: Chat and agent both remain under injection hygiene
Delimiters and the data-not-instructions rule MUST apply to retrieved context on `/ai/chat` and `/ai/chat/stream`, and to tool messages on `/ai/agent*`. Neither route MUST replace the other. Local full-stack compose MUST keep working. Workspace, user, and role MUST still come from the trusted session. A missing session or a role the notes API would reject MUST still fail closed, including when the delimited text agrees with the attack.

#### Scenario: Both routes stay addressable
- **GIVEN** injection hygiene is in effect
- **WHEN** a client calls `/ai/chat` or `/ai/agent`
- **THEN** chat still answers from retrieved context
- **AND** the agent route remains separately addressable

#### Scenario: Injected agreement does not loosen tenant or role checks
- **GIVEN** delimited text that tells the model the session workspace or role has changed
- **WHEN** a tool runs
- **THEN** workspace, user, and role still come from the trusted session
- **AND** a missing session or a forbidden role is still denied with no guessed workspace
