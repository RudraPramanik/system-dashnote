## Purpose

Defines the runtime degrade matrix for the workspace assistant so provider failure, missing HITL persistence, and exhausted AI budget fail visibly and safely without silent empty success responses.

## ADDED Requirements

### Requirement: Provider exhaustion is a user-safe unavailable response
When every configured LLM candidate has failed after the existing fallback walk, chat and agent surfaces MUST return a user-safe unavailable response. Unary `POST /ai/chat` and unary `POST /ai/agent` MUST return HTTP 503 with the message `LLM temporarily unavailable; retry shortly` (or an equivalent detail that includes that text). Streaming `POST /ai/chat/stream` and `POST /ai/agent/stream` MUST emit an SSE object with `type` `error` and that same unavailable message, then end the stream. The response MUST NOT be a silent empty HTTP 200. The response MUST NOT be a bare HTTP 500 whose only cause is total provider exhaustion. Workspace and user identity MUST continue to come from the JWT / harness context. `/ai/chat*` and `/ai/agent*` MUST both remain. `GET /health` MUST remain unaffected.

#### Scenario: Unary chat maps total provider failure to 503
- **GIVEN** every configured LLM candidate is gone, rate-limited, or otherwise exhausted
- **WHEN** a client calls `POST /ai/chat` with a valid JWT
- **THEN** the HTTP status is 503
- **AND** the detail includes `LLM temporarily unavailable; retry shortly`
- **AND** the body is not an empty successful answer

#### Scenario: Chat stream maps total provider failure to an SSE error
- **GIVEN** every configured LLM candidate is exhausted
- **WHEN** a client calls `POST /ai/chat/stream` with a valid JWT
- **THEN** the stream yields an SSE `type: "error"` frame whose message is `LLM temporarily unavailable; retry shortly`
- **AND** the connection does not end as a silent empty 200 success

#### Scenario: Agent unary keeps the same unavailable contract
- **GIVEN** every configured LLM candidate is exhausted
- **WHEN** a client calls `POST /ai/agent` with a valid JWT
- **THEN** the HTTP status is 503
- **AND** the detail includes `LLM temporarily unavailable; retry shortly`

### Requirement: Checkpointer-down blocks mutations and allows search
When the LangGraph checkpointer is not initialized or the mutation checkpointer probe fails, `create_note` and `update_note` MUST NOT persist a note create or update. Those tools MUST return the existing checkpointer / mutation-unavailable signal rather than committing “just this once.” Search and summarize tools MUST remain callable without a checkpointer and MAY return a normal answer or the existing empty-retrieval copy. Direct REST `POST /notes/` MUST NOT depend on the checkpointer. Workspace isolation and note role checks MUST stay in force. `/ai/chat*` and `/ai/agent*` MUST both remain.

#### Scenario: Create does not commit without a checkpointer
- **GIVEN** the API process does not have an initialized LangGraph checkpointer
- **WHEN** the agent `create_note` tool runs
- **THEN** NoteService create is not called
- **AND** no note row is persisted
- **AND** the tool result identifies checkpointer / mutation unavailability

#### Scenario: Update does not commit without a checkpointer
- **GIVEN** the API process does not have an initialized LangGraph checkpointer
- **WHEN** the agent `update_note` tool runs
- **THEN** NoteService update is not called
- **AND** no note content change is persisted
- **AND** the tool result identifies checkpointer / mutation unavailability

#### Scenario: Search may continue without a checkpointer
- **GIVEN** the checkpointer is not initialized
- **AND** retrieval dependencies are otherwise healthy or empty
- **WHEN** the agent `search_notes` tool runs
- **THEN** the tool is not blocked solely because the checkpointer is down
- **AND** it MAY return matches or the empty-retrieval copy

### Requirement: Budget exhaustion stays the existing controlled refusal
When an AI budget ceiling is exceeded, the system MUST reuse the existing AI budget refusal: no provider completion for that request, HTTP 429 on unary chat/agent, and SSE `type` `error` with `code` `budget_exceeded` on streams. This degrade row MUST NOT invent a second budget path, MUST NOT map over-budget to HTTP 500, and MUST NOT weaken Redis fail-open for budget checks. `/health` and `/health/ai` MUST remain independent of AI budget keys. `/ai/chat*` and `/ai/agent*` MUST both remain.

#### Scenario: Over-budget still refuses without a provider call
- **GIVEN** the trusted user-minute or workspace-day counter is already over its ceiling
- **WHEN** a client would start a chat or agent completion
- **THEN** the client receives HTTP 429 or an SSE `budget_exceeded` error
- **AND** the LLM provider client is not called for that completion

### Requirement: Degrade proof does not require a live model key
The repository MUST include automated tests for the provider-unavailable and checkpointer-down rows that run without a live LLM provider key. A failing assertion MUST fail the test run. The budget row MAY be covered by the existing AI budget refusal tests. Provider cooldown and a single harness control-plane module MUST NOT be required for this capability.

#### Scenario: Fixture suite covers provider and checkpointer rows
- **GIVEN** pull-request CI without a hosted model key
- **WHEN** the degrade harness tests run
- **THEN** unary or stream provider exhaustion is asserted as 503 or SSE error
- **AND** checkpointer-down create or update asserts no NoteService commit
- **AND** neither case is skipped to stay green

### Requirement: Chat and agent remain separate under degrade modes
Degrade behavior MUST apply to both `/ai/chat*` and `/ai/agent*` without merging those routes or replacing chat with the agent. Local full-stack compose MUST keep working. No second agent framework is introduced by this capability.

#### Scenario: Both AI surfaces stay mounted
- **WHEN** this capability is enabled
- **THEN** `POST /ai/chat` and `POST /ai/chat/stream` still exist
- **AND** `POST /ai/agent` and `POST /ai/agent/stream` still exist
