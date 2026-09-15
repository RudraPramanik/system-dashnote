## MODIFIED Requirements

### Requirement: Blueprint8 document is the operator-default ship path
The repository MUST include a non-empty `docs/documentation/blueprint8.md` that identifies itself as the operator-default ship path for hiring readiness and AI-engineering depth. Operators MUST be instructed to follow blueprint8 first. The checkbox tracker under that lock MUST be `docs/documentation/blueprint/goal.md`. Historical Composer slice files under `docs/documentation/blueprint/slice*.md` MUST NOT be required as live executable prompts.

#### Scenario: Operator opens blueprint8
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/documentation/blueprint8.md`
- **THEN** the file is non-empty
- **AND** it states that it is the default path to follow
- **AND** it points to `docs/documentation/blueprint/goal.md` for open/closed checkboxes

#### Scenario: Detail blueprints are not orphaned
- **GIVEN** blueprint8 is the default
- **WHEN** an operator needs eval or HITL operator guidance
- **THEN** blueprint8 points at shipped artifacts (`evals/README.md`, `docs/documentation/frontendguide.md`, and/or `docs/documentation/ai.md`)
- **AND** those targets remain valid operator docs (Composer `slice8_eval.md` / `slice8_hitl.md` files are no longer required)

### Requirement: Local AI-depth-first Tier 1 window is documented without hire claims
Operator-facing ship-path docs (`blueprint8.md` and/or `goal.md`) MUST record that the local AI-depth-first Tier 1 window is complete and that VPS work has resumed. Docs MUST authorize HTTP-on-IP first-boot of the thin production compose on the current ~2 GB AWS VPS as the next Alive step. Docs MUST still forbid claiming production-live or job-search readiness until HTTPS A4/A7 smoke exists. Local Tier 1 completion MUST NOT be treated as a waiver of Tier 0 production proof. GraphRAG and multi-agent MUST remain non-goals on the default path.

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

### Requirement: Goal tracker is the ship-path checklist
`docs/documentation/blueprint/goal.md` MUST remain the job-search / hiring checkbox tracker under blueprint8. It MUST NOT instruct operators to follow a contradictory default order. Unique still-open items previously only listed in `docs/ship-plan.md` MUST appear here or in blueprint8 so deleting ship-plan does not drop an open gate.

#### Scenario: Operator uses goal.md instead of ship-plan
- **GIVEN** this change is complete
- **WHEN** an operator looks for remaining hire-gate boxes
- **THEN** they find them in `goal.md` (and/or blueprint8)
- **AND** they are not required to open `docs/ship-plan.md`

## REMOVED Requirements

### Requirement: Ship-plan locks to blueprint8
**Reason**: `docs/ship-plan.md` duplicated blueprint8 law and goal.md checkboxes; the day-by-day file is no longer a live source of truth.
**Migration**: Follow `docs/documentation/blueprint8.md` for the locked path and `docs/documentation/blueprint/goal.md` for remaining boxes.
