## ADDED Requirements

### Requirement: Local AI-depth-first Tier 1 window is documented without hire claims
Operator-facing ship-path docs (`blueprint8.md` and/or `goal.md` / `ship-plan.md` as appropriate) MUST allow executing Tier 1 deepeners (HITL, Langfuse depth, trajectory goldens, fixture CI) against the local Alive stack when VPS A-gate is deferred, and MUST state that this follows the alternate AI-depth-first window—not a waiver of Tier 0 production proof. Docs MUST forbid claiming production-live or job-search readiness solely because local Tier 1 work is complete.

#### Scenario: Operator can start local Tier 1 without VPS
- **GIVEN** local API/FE are demoable and C-gate harness exists
- **AND** HTTPS prod smoke is not yet proven
- **WHEN** an operator reads the ship-path guidance for this window
- **THEN** they are authorized to implement Tier 1 deepeners locally
- **AND** they are told not to claim production-live or hire-ready until A-gate evidence exists

#### Scenario: Deploy-first remains the long-term default
- **GIVEN** the same docs
- **WHEN** VPS work resumes
- **THEN** closing A4/A7 smoke remains required before production-live claims
- **AND** GraphRAG / multi-agent remain non-goals on the default path
