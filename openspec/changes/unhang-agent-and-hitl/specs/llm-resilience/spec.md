## ADDED Requirements

### Requirement: LLM candidates are tried in order on timeout as well as model gone
When a completion (stream or non-stream) exceeds the configured per-call wall clock (`AGENT_TOOL_TIMEOUT` seconds) or is otherwise retry-exhausted without a response, the system MUST abort that candidate and retry the same request with the next unused `LLM_MODEL` / `LLM_MODEL_FALLBACKS` id. A hung provider connection MUST NOT hold the caller indefinitely. Workspace and user identity MUST continue to come from JWT / request context, never from the model id. Provider SDK timeouts alone MUST NOT be treated as sufficient if they fail to abort.

#### Scenario: Primary hangs, fallback succeeds
- **GIVEN** the primary candidate does not return within the configured wall clock
- **AND** `LLM_MODEL_FALLBACKS` contains a later live id
- **WHEN** a client calls `POST /ai/chat/stream` or `POST /ai/agent/stream` with a valid JWT
- **THEN** the request MUST complete using a later candidate
- **AND** MUST NOT remain open for minutes after the wall clock

#### Scenario: Agent tool RAG uses the same wall clock
- **GIVEN** the workspace agent invokes search or summarize (RAG completion inside a tool)
- **AND** that completion hangs past the configured wall clock
- **WHEN** a later candidate is live
- **THEN** the tool path MUST abort the hung candidate and continue with the next id
- **AND** MUST NOT leave `POST /ai/agent/stream` without tokens or an `error` frame indefinitely

#### Scenario: All candidates time out
- **GIVEN** every configured candidate exceeds the wall clock or is unreachable
- **WHEN** a client calls `POST /ai/chat/stream` or `POST /ai/agent/stream`
- **THEN** the stream MUST yield an SSE `type: "error"` frame whose `message` is `LLM temporarily unavailable; retry shortly`
- **AND** `GET /health` MUST remain unaffected

### Requirement: Default candidates prefer a live small model then Gemini
Documented and example defaults MUST list a currently live small NVIDIA NIM id first (Nemotron 3.5 Lightning class, or Gemini Flash if that NIM id is gone for the operator) and MUST include `gemini/gemini-2.5-flash` as a fallback when a Gemini key is configured. Default `LLM_MODEL_FALLBACKS` MUST NOT include Nemotron Super 120B or Ultra 550B as a hop. Operators MAY still set those ids explicitly. Completions MUST NOT enable unbounded hidden reasoning traces that ignore `LLM_MAX_TOKENS`.

#### Scenario: Example env does not pin dead nano or 120B as the safety net
- **GIVEN** an operator copies `.env.example` without overriding model ids
- **WHEN** they inspect `LLM_MODEL` and `LLM_MODEL_FALLBACKS`
- **THEN** the primary MUST NOT be the retired Nemotron 3 Nano id
- **AND** Super 120B MUST NOT appear as the first fallback
- **AND** Gemini Flash MUST appear in the candidate list

#### Scenario: Operator may still pin a heavy NIM
- **GIVEN** an operator sets `LLM_MODEL` to a 120B id on purpose
- **WHEN** that id is live
- **THEN** the system MUST still honor that explicit setting
- **AND** the wall-clock abort and fallback rules still apply

### Requirement: Quiet AI streams stay alive then fail visibly
`POST /ai/chat/stream` and `POST /ai/agent/stream` served through the Compose nginx edge MUST keep the SSE connection from being cut solely because no tokens arrived yet within a typical 60s proxy default. The stream MUST emit keep-alive traffic until a `token`, `error`, `done`, or `approval_required` frame (agent) is produced, or until the wall-clock policy yields an `error` frame. Chat and agent routes MUST both remain.

#### Scenario: Agent stream survives a slow first token
- **GIVEN** the first LLM completion takes longer than 60 seconds but still finishes inside the configured wall clock
- **WHEN** a client reads `POST /ai/agent/stream` via nginx on port 80
- **THEN** the connection MUST still be open to receive the first `token`, `tool_start`, `approval_required`, `done`, or `error` frame
- **AND** MUST NOT drop silently with HTTP 200 and an empty body

#### Scenario: Chat and agent both remain after stream hardening
- **WHEN** this capability is enabled
- **THEN** `POST /ai/chat` and `POST /ai/chat/stream` still exist
- **AND** `POST /ai/agent` and `POST /ai/agent/stream` still exist
