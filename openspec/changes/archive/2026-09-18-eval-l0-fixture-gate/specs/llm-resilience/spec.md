## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Default candidates prefer a live small model then Gemini
Documented and example defaults MUST list a currently live small NVIDIA NIM id first (Nemotron 3.5 Lightning class, or Gemini Flash if that NIM id is gone for the operator). `LLM_MODEL_FALLBACKS` MUST include at least one additional currently-live NVIDIA NIM free/catalog id distinct from the primary, then `gemini/gemini-2.5-flash` when a Gemini key is configured, so Gemini quota can be skipped in favor of another NIM model. Default `LLM_MODEL_FALLBACKS` MUST NOT include Nemotron Super 120B or Ultra 550B as a hop. Operators MAY still set those ids explicitly. Completions MUST NOT enable unbounded hidden reasoning traces that ignore `LLM_MAX_TOKENS`.

#### Scenario: Example env does not pin dead nano or 120B as the safety net
- **GIVEN** an operator copies `.env.example` without overriding model ids
- **WHEN** they inspect `LLM_MODEL` and `LLM_MODEL_FALLBACKS`
- **THEN** the primary MUST NOT be the retired Nemotron 3 Nano id
- **AND** Super 120B MUST NOT appear as the first fallback
- **AND** Gemini Flash MUST appear in the candidate list
- **AND** `LLM_MODEL_FALLBACKS` MUST include a NVIDIA NIM id different from the primary

#### Scenario: Operator may still pin a heavy NIM
- **GIVEN** an operator sets `LLM_MODEL` to a 120B id on purpose
- **WHEN** that id is live
- **THEN** the system MUST still honor that explicit setting
- **AND** the wall-clock abort, model-gone, and rate-limit fallback rules still apply

#### Scenario: Operator can swap a different free NIM when Gemini is quota-blocked
- **GIVEN** Gemini Flash is rate-limited
- **AND** documented fallbacks include another live NVIDIA NIM free/catalog id
- **WHEN** a completion walks candidates
- **THEN** that NVIDIA NIM id is eligible before the process fails closed
- **AND** the operator is not required to wait for Gemini quota to reset
