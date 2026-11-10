## MODIFIED Requirements

### Requirement: Degrade proof does not require a live model key
The repository MUST include automated tests for the provider-unavailable, checkpointer-down, and provider-cooldown rows that run without a live LLM provider key. A failing assertion MUST fail the test run. The budget row MAY be covered by the existing AI budget refusal tests. Provider-unavailable and budget denials for chat and agent generation MUST be reachable through the shared harness control plane required by the `ai-harness-control-plane` capability. Checkpointer-down mutation fail-closed MAY remain enforced at the tool / HITL boundary.

#### Scenario: Fixture suite covers provider and checkpointer rows
- **GIVEN** pull-request CI without a hosted model key
- **WHEN** the degrade and LLM resilience harness tests run
- **THEN** unary or stream provider exhaustion is asserted as 503 or SSE error
- **AND** checkpointer-down create or update asserts no NoteService commit
- **AND** a primary in cooldown asserts the next fallback is used, and after expiry the primary is eligible again
- **AND** none of those cases is skipped to stay green
