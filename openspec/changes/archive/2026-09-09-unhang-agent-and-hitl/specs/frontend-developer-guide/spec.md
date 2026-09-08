## ADDED Requirements

### Requirement: Agent client handles approval_required then resume or reject
The frontend guide MUST document that `POST /ai/agent/stream` may emit `type: "approval_required"` with `tool`, `args`, `thread_id`, and `interrupt_id`, then close the stream. The agent UI MUST then show Approve and Reject. Approve maps to `POST /ai/agent/resume`; reject maps to `POST /ai/agent/reject`. Bodies MUST be limited to `thread_id` and optional `interrupt_id` per OpenAPI. The client MUST NOT send `workspace_id` to override JWT tenancy. The client MUST NOT auto-approve mutations. Chat (`/ai/chat*`) MUST remain a separate mode without this gate.

#### Scenario: Guide describes the approval event
- **WHEN** a frontend implements the agent view
- **THEN** the guide MUST list `approval_required` alongside `token`, `tool_start`, `tool_end`, `done`, and `error`
- **AND** MUST document ending the stream after `approval_required` and reconnecting via resume or reject

#### Scenario: Guide forbids tenant override on resume
- **WHEN** the client calls `/ai/agent/resume` or `/ai/agent/reject`
- **THEN** the guide MUST state that workspace comes from the JWT only
- **AND** MUST forbid a client-chosen `workspace_id` on those bodies

### Requirement: Quiet or empty agent streams fail visibly
The frontend guide MUST require that if an agent (or chat) stream closes with no `token` content, no `done`, no `approval_required`, and no `error` frame, the UI MUST show a user-visible failure (calm copy consistent with LLM unavailability) instead of an empty assistant bubble. A hung wait with no Cancel path MUST NOT be documented as success.

#### Scenario: Empty stream is an error
- **WHEN** `POST /ai/agent/stream` returns HTTP 200 then the body ends without a parsed `token`, `done`, `approval_required`, or `error` event
- **THEN** the documented UI MUST show a visible error
- **AND** MUST NOT leave the user with only a blank reply

## MODIFIED Requirements

### Requirement: AI chat, agent, and threads client contracts
The guide SHALL document AI surfaces as coexisting features with explicit streaming and citation rules.

#### Scenario: Chat and agent coexist
- **WHEN** a frontend designs AI UI
- **THEN** the guide MUST present `/ai/chat` and `/ai/chat/stream` (fast RAG) and `/ai/agent` and `/ai/agent/stream` (tool loop) as separate modes that MUST both remain available

#### Scenario: SSE citations from metadata only
- **WHEN** a frontend consumes a streaming AI response
- **THEN** the guide MUST require rendering answer tokens from `type: token` events and citations (or equivalent source metadata) only from the final `type: metadata` event — never by parsing citations out of the token text stream

#### Scenario: Threads for conversation continuity
- **WHEN** a frontend implements chat history
- **THEN** the guide MUST document thread list/messages endpoints under `/ai` and how optional `thread_id` continues a conversation

#### Scenario: Agent tool events for UI
- **WHEN** a frontend implements the agent view
- **THEN** the guide MUST describe how to surface tool progress (e.g. tool start/end style events) for a multi-step demo without treating the agent as a replacement for RAG chat
- **AND** MUST describe `approval_required` plus in-thread Approve/Reject for `create_note` / `update_note` so the demo path "agent creates/updates note" can complete
