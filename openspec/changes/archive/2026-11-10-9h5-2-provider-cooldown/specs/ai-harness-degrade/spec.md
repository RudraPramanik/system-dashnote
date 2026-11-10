## ADDED Requirements

### Requirement: Repeated provider 429 or 5xx cools down then uses existing fallbacks
When one configured LLM candidate repeatedly returns HTTP 429 or HTTP 5xx (or equivalent rate-limit / upstream errors), the harness degrade matrix MUST cool that model id down for a short window and skip it on later completions while continuing the existing `LLM_MODEL` / `LLM_MODEL_FALLBACKS` order. When the window ends, the id MUST be eligible again. If every candidate is cooling down or failing, chat and agent MUST keep the existing user-safe unavailable response (HTTP 503 or SSE error with `LLM temporarily unavailable; retry shortly`). Cooldown MUST NOT require Redis, MUST NOT invent a second agent framework, MUST NOT merge `/ai/chat*` into `/ai/agent*`, and MUST NOT weaken checkpointer-down fail-closed mutations or the existing AI budget refusal. Workspace and user identity MUST continue to come from the JWT / harness context.

#### Scenario: Cooldown skips a failing primary then recovers
- **GIVEN** the primary candidate has entered cooldown after repeated 429 or 5xx
- **AND** a later fallback id is live
- **WHEN** a subsequent AI completion runs before the cooldown expires
- **THEN** the completion uses the later fallback
- **AND** after the cooldown expires the primary is eligible again

#### Scenario: All-cooling still maps to unavailable
- **GIVEN** every configured candidate is cooling down or fails when tried
- **WHEN** a client calls a chat or agent generation route
- **THEN** the client receives the existing user-safe unavailable response
- **AND** the response is not a silent empty HTTP 200

## MODIFIED Requirements

### Requirement: Degrade proof does not require a live model key
The repository MUST include automated tests for the provider-unavailable, checkpointer-down, and provider-cooldown rows that run without a live LLM provider key. A failing assertion MUST fail the test run. The budget row MAY be covered by the existing AI budget refusal tests. A single harness control-plane module MUST NOT be required for this capability.

#### Scenario: Fixture suite covers provider and checkpointer rows
- **GIVEN** pull-request CI without a hosted model key
- **WHEN** the degrade and LLM resilience harness tests run
- **THEN** unary or stream provider exhaustion is asserted as 503 or SSE error
- **AND** checkpointer-down create or update asserts no NoteService commit
- **AND** a primary in cooldown asserts the next fallback is used, and after expiry the primary is eligible again
- **AND** none of those cases is skipped to stay green
