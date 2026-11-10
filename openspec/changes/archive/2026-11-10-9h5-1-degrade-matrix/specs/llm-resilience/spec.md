## ADDED Requirements

### Requirement: Unary chat returns 503 when every candidate is unavailable
When every configured `LLM_MODEL` / `LLM_MODEL_FALLBACKS` candidate has failed for a non-streaming RAG completion (gone, rate-limited, timed out, or otherwise exhausted after the existing fallback walk), `POST /ai/chat` MUST return HTTP 503 whose detail includes `LLM temporarily unavailable; retry shortly`. The response MUST NOT be HTTP 200 with an empty or placeholder answer solely because providers failed. The response MUST NOT be a bare HTTP 500 whose only cause is that exhaustion. Streaming chat MUST keep emitting an SSE `type: "error"` frame with that same message. Workspace and user identity MUST continue to come from the JWT. `GET /health` MUST remain unaffected. `/ai/chat*` and `/ai/agent*` MUST both remain.

#### Scenario: Unary chat maps total candidate failure to 503
- **GIVEN** every configured candidate is gone, rate-limited, or unreachable
- **WHEN** a client calls `POST /ai/chat` with a valid JWT
- **THEN** the HTTP status is 503
- **AND** the detail includes `LLM temporarily unavailable; retry shortly`
- **AND** the response is not an empty successful chat answer

#### Scenario: Stream chat keeps the existing SSE unavailable frame
- **GIVEN** every configured candidate is exhausted
- **WHEN** a client calls `POST /ai/chat/stream` with a valid JWT
- **THEN** the stream yields an SSE `type: "error"` frame whose `message` is `LLM temporarily unavailable; retry shortly`
- **AND** `GET /health` is unaffected
