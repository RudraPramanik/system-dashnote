## ADDED Requirements

### Requirement: Default candidates prefer Gemini Flash then a small NIM
Documented code defaults and example env files MUST set `LLM_MODEL` to `gemini/gemini-2.5-flash`. `LLM_MODEL_FALLBACKS` MUST list a currently live small NVIDIA NIM id (Nemotron 3.5 Lightning class) that is distinct from the primary, and MUST NOT list `nvidia_nim/openai/gpt-oss-20b`, Nemotron Super 120B, or Ultra 550B. Operators MAY still set any of those ids explicitly, including a 120B primary. Completions MUST NOT enable unbounded hidden reasoning traces that ignore `LLM_MAX_TOKENS`. Chat and agent routes MUST both remain. Gone, timeout, and rate-limit candidate walks MUST keep their existing order and error frames.

#### Scenario: Example env does not pin gpt-oss or 120B
- **GIVEN** an operator copies `.env.example` or `.env.production.example` without overriding model ids
- **WHEN** they inspect `LLM_MODEL` and `LLM_MODEL_FALLBACKS`
- **THEN** the primary is `gemini/gemini-2.5-flash`
- **AND** `gpt-oss-20b` does not appear
- **AND** Super 120B does not appear
- **AND** a Lightning-class NVIDIA NIM id appears as a fallback distinct from the primary

#### Scenario: Operator may still pin a heavy or hanging id
- **GIVEN** an operator sets `LLM_MODEL` to a 120B id or to `nvidia_nim/openai/gpt-oss-20b` on purpose
- **WHEN** that id is live
- **THEN** the system MUST still honor that explicit setting
- **AND** the wall-clock abort, model-gone, and rate-limit fallback rules still apply

#### Scenario: Gemini rate-limit can still walk to NIM
- **GIVEN** Gemini Flash is rate-limited
- **AND** the Lightning-class fallback is live
- **WHEN** a completion walks candidates
- **THEN** that NVIDIA NIM id is eligible before the process fails closed
- **AND** the operator is not required to wait for Gemini quota to reset

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

## REMOVED Requirements

### Requirement: Default candidates prefer a live small model then Gemini
**Reason**: A NIM-first default let the health probe cache `nvidia_nim/openai/gpt-oss-20b` after Lightning failed to answer in time. That id is the hang risk on hosted chat, and it is not what operators see as the configured primary.
**Migration**: Defaults and example env files use `gemini/gemini-2.5-flash` first and a Lightning-class NIM as the fallback. Operators who want NIM-first set `LLM_MODEL` themselves. `gpt-oss-20b` is no longer a default hop. Recreate the API container after changing the VPS env so the in-process cache clears.
