## Purpose

Defines one harness control plane that chat and agent routes call for trusted tenant context, AI budget gating, and typed denial mapping so routes stay thin HTTP and SSE adapters over the existing RagService and LangGraph assistant.

## ADDED Requirements

### Requirement: One harness entry for chat and agent generation
Chat and agent generation surfaces MUST obtain trusted tenant context construction, the AI request-budget check, and provider-unavailable / known-denial mapping from one shared harness control-plane module. `POST /ai/chat`, `POST /ai/chat/stream`, `POST /ai/agent`, and `POST /ai/agent/stream` MUST use that module rather than each route reimplementing Redis AI budget key consumption or duplicating the 429 / 503 / SSE denial mapping. Two entrypoints in the same module (for example chat versus agent, or unary versus stream) are allowed. Copying the budget check into both route modules is forbidden. LangGraph remains the agent loop. RagService remains the fast RAG path. `/ai/chat*` and `/ai/agent*` MUST both remain. Workspace identity MUST continue to come from the JWT / harness context. No second agent framework is introduced.

#### Scenario: Both surfaces share one control-plane module
- **GIVEN** an authenticated caller
- **WHEN** they invoke chat generation or agent generation
- **THEN** trusted context bind and the AI budget gate are performed through the shared harness control-plane module
- **AND** neither route module owns a second inline Redis AI budget consumption path

#### Scenario: Chat and agent stay separate adapters
- **WHEN** the control plane is enabled
- **THEN** `POST /ai/chat` and `POST /ai/chat/stream` still exist
- **AND** `POST /ai/agent` and `POST /ai/agent/stream` still exist
- **AND** those routes are not merged into one product surface

### Requirement: Known harness denials map to typed client errors
When the harness control plane denies a request for budget exhaustion, a forbidden / missing trusted-context condition, or total provider unavailability, chat and agent routes MUST surface the existing client contracts: HTTP 429 (or SSE `budget_exceeded`) for over-budget, HTTP 403 (or the existing forbidden tool/route contract) for forbidden / missing trusted context where that applies, and HTTP 503 (or SSE error with `LLM temporarily unavailable; retry shortly`) for provider exhaustion. Those known denials MUST NOT be remapped to a bare HTTP 500 by a catch-all. Unexpected exceptions MAY still be 500. Redis budget fail-open behavior MUST remain. `/health` and `/health/ai` MUST remain independent of AI budget keys.

#### Scenario: Budget denial stays 429 or SSE budget_exceeded
- **GIVEN** the trusted user-minute or workspace-day counter is already over its ceiling
- **WHEN** a client would start a chat or agent completion through the control plane
- **THEN** the client receives HTTP 429 or an SSE `budget_exceeded` error
- **AND** the LLM provider client is not called for that completion
- **AND** the status is not 500 solely because of that denial

#### Scenario: Provider exhaustion stays 503 or SSE unavailable
- **GIVEN** every configured LLM candidate is exhausted after fallback and cooldown
- **WHEN** a client calls a chat or agent generation route through the control plane
- **THEN** the client receives HTTP 503 or an SSE error whose message includes `LLM temporarily unavailable; retry shortly`
- **AND** the response is not a silent empty HTTP 200
- **AND** the status is not a bare 500 whose only cause is total provider exhaustion

### Requirement: Control-plane proof does not require a live model key
The repository MUST include automated coverage that routes no longer perform a second inline AI budget consumption path, and that a harness denial for over-budget or provider-unavailable produces 429 or 503 (or the matching SSE error). Existing chat citation behavior and agent HITL approval events MUST still pass their tests. These checks MUST run without a live LLM provider key. A failing assertion MUST fail the test run.

#### Scenario: Fixture suite covers thin-route denials
- **GIVEN** pull-request CI without a hosted model key
- **WHEN** the harness control-plane and related AI route tests run
- **THEN** over-budget still yields 429 or SSE `budget_exceeded` without a provider call
- **AND** provider exhaustion still yields 503 or the unavailable SSE error
- **AND** citation and HITL approval coverage still pass
- **AND** none of those cases is skipped to stay green
