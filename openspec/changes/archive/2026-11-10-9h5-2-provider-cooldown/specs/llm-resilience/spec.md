## ADDED Requirements

### Requirement: Transient provider failures use a time-bounded cooldown
When a configured `LLM_MODEL` / `LLM_MODEL_FALLBACKS` candidate fails with HTTP 429 (or an equivalent provider rate-limit error) or with HTTP 5xx (or an equivalent upstream server error) enough times that the completion walk leaves that candidate, the system MUST mark that model id as cooling down for a short window controlled by `LLM_PROVIDER_COOLDOWN_SECONDS`. While the id is cooling down, later completions in that process MUST skip it and continue the existing candidate order. When the cooldown window ends, the id MUST become eligible again. Cooldown storage MUST be in-process for the API worker; it MUST NOT require Redis. Cooldown MUST NOT stick forever. Model-gone / end-of-life candidates MAY remain durably skipped and MUST NOT be rewritten into the same timer as transient 429/5xx. Workspace and user identity MUST continue to come from the JWT / harness context, never from the model id. Chat and agent routes MUST both remain. If every candidate is cooling down or failing, the system MUST return the existing user-safe unavailable response (`LLM temporarily unavailable; retry shortly`) and MUST NOT loop forever. `GET /health` MUST remain unaffected. `LLM_PROVIDER_COOLDOWN_SECONDS` MUST load from settings as a positive integer default documented as a default, not a frozen production quota.

#### Scenario: Primary in cooldown yields the next fallback
- **GIVEN** the primary model id is marked cooling down after repeated 429 or 5xx
- **AND** a later `LLM_MODEL_FALLBACKS` id is live
- **WHEN** a subsequent chat or agent completion runs in the same process before the cooldown expires
- **THEN** the completion uses the later fallback id
- **AND** it does not call the cooling primary first

#### Scenario: Primary is eligible again after cooldown expires
- **GIVEN** the primary model id was cooling down
- **AND** the cooldown window has ended
- **WHEN** a later chat or agent completion runs in the same process
- **THEN** the primary id is eligible to be tried again
- **AND** the cooldown does not remain permanent for that process lifetime solely because of the earlier 429 or 5xx

#### Scenario: All candidates cooling or failing stay user-safe unavailable
- **GIVEN** every configured candidate is cooling down or fails when tried
- **WHEN** a client calls `POST /ai/chat`, `POST /ai/chat/stream`, `POST /ai/agent`, or `POST /ai/agent/stream` with a valid JWT
- **THEN** the client receives HTTP 503 or an SSE `type: "error"` whose message includes `LLM temporarily unavailable; retry shortly`
- **AND** the process does not spin forever across the same candidate list
- **AND** `GET /health` is unaffected

#### Scenario: Cooldown does not need Redis and stays process-local
- **GIVEN** Redis is unavailable or unused for LLM candidate state
- **WHEN** a candidate enters cooldown after 429 or 5xx
- **THEN** later requests in that same process still skip the cooling id
- **AND** the system does not require a Redis cooldown key to enforce the skip

## MODIFIED Requirements

### Requirement: LLM candidates are tried in order on provider rate-limit
When a completion (stream or non-stream) fails because the current candidate is rate-limited (HTTP 429 or an equivalent provider quota / rate-limit error), the system MUST retry the same request with the next unused `LLM_MODEL` / `LLM_MODEL_FALLBACKS` id. The rate-limited id MUST enter the time-bounded cooldown for subsequent requests in that process and MUST NOT remain the sticky cached success while cooling. After the cooldown expires, the id MAY be selected again. Workspace and user identity MUST continue to come from JWT / request context, never from the model id. Chat and agent routes MUST both remain; fallback MUST NOT merge `/ai/chat*` into `/ai/agent*`.

#### Scenario: Gemini 429 walks to NVIDIA NIM
- **GIVEN** the current candidate returns HTTP 429 or a rate-limit error
- **AND** a later candidate is a live NVIDIA NIM id
- **WHEN** a client calls `POST /ai/chat` or `POST /ai/chat/stream` with a valid JWT
- **THEN** the request completes using the later NVIDIA NIM candidate
- **AND** the HTTP status is not forced to 5xx solely because the prior candidate was rate-limited

#### Scenario: Rate-limited id is not sticky
- **GIVEN** a candidate returned 429 and a later candidate succeeded
- **AND** the rate-limited id is still inside its cooldown window
- **WHEN** a subsequent chat or agent completion runs in the same process
- **THEN** the system MUST NOT select the rate-limited id as the cached primary
- **AND** it MUST prefer a candidate that is not cooling down for rate-limit

#### Scenario: All candidates rate-limited or unavailable
- **GIVEN** every configured candidate returns 429, is gone, exceeds the wall clock, or is cooling down
- **WHEN** a client calls `POST /ai/chat/stream` or `POST /ai/agent/stream`
- **THEN** the stream yields an SSE `type: "error"` frame whose `message` is `LLM temporarily unavailable; retry shortly`
- **AND** `GET /health` is unaffected

#### Scenario: Agent uses the same rate-limit walk
- **GIVEN** the current candidate is rate-limited and a later NVIDIA NIM id is live
- **WHEN** a client calls `POST /ai/agent` or `POST /ai/agent/stream` with a valid JWT
- **THEN** the agent uses the later candidate instead of failing on the first 429
