## MODIFIED Requirements

### Requirement: Local AI-depth-first Tier 1 window is documented without hire claims
Operator-facing ship-path docs (`blueprint8.md` and/or `goal.md` / `ship-plan.md` as appropriate) MUST record that the local AI-depth-first Tier 1 window is complete and that VPS work has resumed. Docs MUST authorize HTTP-on-IP first-boot of the thin production compose on the current ~2 GB AWS VPS as the next Alive step. Docs MUST still forbid claiming production-live or job-search readiness until HTTPS A4/A7 smoke exists. Local Tier 1 completion MUST NOT be treated as a waiver of Tier 0 production proof. GraphRAG and multi-agent MUST remain non-goals on the default path.

#### Scenario: Operator can start local Tier 1 without VPS
- **GIVEN** local API/FE are demoable and C-gate harness exists
- **AND** HTTPS prod smoke is not yet proven
- **WHEN** an operator reads historical guidance for the closed local-only window
- **THEN** they still understand local Tier 1 was allowed during deferral
- **AND** they are told not to claim production-live or hire-ready from local work alone

#### Scenario: Deploy-first remains the long-term default
- **GIVEN** the same docs
- **WHEN** VPS work resumes without a domain
- **THEN** HTTP-on-IP first-boot of api/worker/nginx against hosted services is the next required Alive step
- **AND** closing HTTPS A4/A7 smoke remains required before production-live claims
- **AND** GraphRAG / multi-agent remain non-goals on the default path

## ADDED Requirements

### Requirement: Current compute is a 2 GB thin VPS
Blueprint8 and platform topology docs MUST describe the production compute box as a small VPS (~2 GB RAM, hosted data plane) rather than an 8 GB in-box data-plane host. Alive law MUST continue: VPS-hostile lab work stays off this box.

#### Scenario: Topology matches the t3.small
- **GIVEN** an operator reads production topology / Alive VPS notes after this change
- **WHEN** they plan what runs on the VPS
- **THEN** they see ~2 GB AWS (or equivalent) thin compute with hosted Postgres, Redis, Qdrant, and object storage
- **AND** they do not treat an 8 GB Oracle-with-local-data-plane layout as current
