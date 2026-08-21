## Purpose

Keeps RAG chat and the workspace agent answering when a pinned hosted LLM id is retired (HTTP 410 / not found) by walking an operator-configured candidate list, without making the LLM a hard process or deploy dependency.

## ADDED Requirements

### Requirement: LLM candidates are tried in order on model gone
The system MUST treat `LLM_MODEL` as the first candidate and `LLM_MODEL_FALLBACKS` as additional LiteLLM ids (comma-separated, empty allowed). When a completion (stream or non-stream) fails because the model is gone (HTTP 410, end-of-life, or model not found), the system MUST retry the same request with the next unused candidate. Workspace and user identity MUST continue to come from JWT / request context, never from the model id.

#### Scenario: Primary model gone, fallback succeeds
- **GIVEN** `LLM_MODEL` is a retired hosted id
- **AND** `LLM_MODEL_FALLBACKS` contains a live id
- **WHEN** a client calls `POST /ai/chat/stream` or `POST /ai/agent/stream` with a valid JWT
- **THEN** the request completes using a later candidate
- **AND** the HTTP status is not forced to 5xx solely because the primary id returned 410

#### Scenario: All candidates gone
- **GIVEN** every configured candidate is gone or unreachable
- **WHEN** a client calls `POST /ai/chat/stream`
- **THEN** the stream yields an SSE `type: "error"` frame whose `message` is `LLM temporarily unavailable; retry shortly`
- **AND** core `GET /health` is unaffected

#### Scenario: Agent stream uses the same candidate policy
- **GIVEN** the primary model is gone and a fallback is live
- **WHEN** a client calls `POST /ai/agent/stream` with a valid JWT
- **THEN** the agent uses a working candidate instead of failing on the first 410

### Requirement: Startup resolve does not block the API
API and worker startup MUST attempt to resolve a working candidate without blocking process boot. If no candidate works, the process MUST stay up and AI routes MUST degrade as specified above.

#### Scenario: API boots when every LLM candidate is down
- **GIVEN** all LLM candidates return gone or connection errors
- **WHEN** the API process starts
- **THEN** the process remains up
- **AND** `GET /health` still reflects only Postgres and Redis

### Requirement: Chat and agent remain separate paths
Fallback MUST apply to both `/ai/chat*` and `/ai/agent*` without merging those routes or replacing chat with the agent.

#### Scenario: Chat and agent both remain
- **WHEN** this capability is enabled
- **THEN** `POST /ai/chat` and `POST /ai/chat/stream` still exist
- **AND** `POST /ai/agent` and `POST /ai/agent/stream` still exist
