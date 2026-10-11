## Purpose

Keeps RAG chat and the workspace agent answering when a pinned hosted LLM id is retired (HTTP 410 / not found) by walking an operator-configured candidate list, without making the LLM a hard process or deploy dependency.

## Requirements

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

### Requirement: LLM candidates are tried in order on provider rate-limit
When a completion (stream or non-stream) fails because the current candidate is rate-limited (HTTP 429 or an equivalent provider quota / rate-limit error), the system MUST retry the same request with the next unused `LLM_MODEL` / `LLM_MODEL_FALLBACKS` id. The rate-limited id MUST NOT remain the cached success for later requests in that process. Workspace and user identity MUST continue to come from JWT / request context, never from the model id. Chat and agent routes MUST both remain; fallback MUST NOT merge `/ai/chat*` into `/ai/agent*`.

#### Scenario: Gemini 429 walks to NVIDIA NIM
- **GIVEN** the current candidate returns HTTP 429 or a rate-limit error
- **AND** a later candidate is a live NVIDIA NIM id
- **WHEN** a client calls `POST /ai/chat` or `POST /ai/chat/stream` with a valid JWT
- **THEN** the request completes using the later NVIDIA NIM candidate
- **AND** the HTTP status is not forced to 5xx solely because the prior candidate was rate-limited

#### Scenario: Rate-limited id is not sticky
- **GIVEN** a candidate returned 429 and a later candidate succeeded
- **WHEN** a subsequent chat or agent completion runs in the same process
- **THEN** the system MUST NOT select the rate-limited id as the cached primary
- **AND** it MUST prefer a candidate that was not marked rate-limited

#### Scenario: All candidates rate-limited or unavailable
- **GIVEN** every configured candidate returns 429, is gone, or exceeds the wall clock
- **WHEN** a client calls `POST /ai/chat/stream` or `POST /ai/agent/stream`
- **THEN** the stream yields an SSE `type: "error"` frame whose `message` is `LLM temporarily unavailable; retry shortly`
- **AND** `GET /health` is unaffected

#### Scenario: Agent uses the same rate-limit walk
- **GIVEN** the current candidate is rate-limited and a later NVIDIA NIM id is live
- **WHEN** a client calls `POST /ai/agent` or `POST /ai/agent/stream` with a valid JWT
- **THEN** the agent uses the later candidate instead of failing on the first 429

### Requirement: Default candidates prefer Lightning NIM then Gemini
Documented code defaults and example env files MUST set `LLM_MODEL` to `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b`. `LLM_MODEL_FALLBACKS` MUST list `gemini/gemini-2.5-flash` when a Gemini key is expected, and MUST NOT list `nvidia_nim/openai/gpt-oss-20b`, Nemotron Super 120B, or Ultra 550B. Operators MAY still pin Super 120B, Ultra, or `gpt-oss-20b` explicitly. Completions MUST NOT enable unbounded hidden reasoning traces that ignore `LLM_MAX_TOKENS`. Chat and agent routes MUST both remain. Gone, timeout, and rate-limit walks MUST keep their existing order and error frames. Documentation MUST note that NIM free tiers are typically higher RPM than Gemini free tiers, so product defaults prefer the small NIM id for routine chat.

#### Scenario: Example env prefers Lightning then Gemini
- **GIVEN** an operator copies `.env.example` or `.env.production.example` without overriding model ids
- **WHEN** they inspect `LLM_MODEL` and `LLM_MODEL_FALLBACKS`
- **THEN** the primary is `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b`
- **AND** the fallback includes `gemini/gemini-2.5-flash`
- **AND** `gpt-oss-20b` does not appear
- **AND** Super 120B does not appear

#### Scenario: Operator may still pin Super for quality
- **GIVEN** an operator sets `LLM_MODEL` to `nvidia_nim/nvidia/nemotron-3-super-120b-a12b`
- **AND** `LLM_MODEL_FALLBACKS` includes Gemini Flash
- **WHEN** that Super id is live
- **THEN** the system MUST honor the explicit Super primary
- **AND** the wall-clock abort, model-gone, and rate-limit fallback rules still apply

#### Scenario: NIM rate-limit walks to Gemini
- **GIVEN** Lightning returns HTTP 429 or a rate-limit error
- **AND** Gemini Flash is live
- **WHEN** a completion walks candidates
- **THEN** the request completes using Gemini Flash
- **AND** the rate-limited NIM id is not sticky as the cached primary

### Requirement: Soft health shows configured and cached models
`GET /health/ai` MUST report the configured `LLM_MODEL` and, when a candidate has been resolved, the cached model that the next completion will try first. The two values MUST stay distinct fields so an operator can see when a fallback has stuck. The probe MUST NOT print provider keys. `GET /health` MUST remain limited to Postgres and Redis. A failed LLM probe MUST NOT take the API process down.

#### Scenario: Cached fallback is visible
- **GIVEN** the configured primary is Gemini Flash
- **AND** the process has cached a different live fallback
- **WHEN** a client calls `GET /health/ai`
- **THEN** the body includes the configured primary and the cached model as separate fields
- **AND** `GET /health` is unaffected

#### Scenario: No cache yet
- **GIVEN** no candidate has been resolved in this process
- **WHEN** a client calls `GET /health/ai`
- **THEN** the configured primary is still reported
- **AND** the cached model is absent or null

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
