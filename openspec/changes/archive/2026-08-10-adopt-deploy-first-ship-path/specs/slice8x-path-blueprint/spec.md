## MODIFIED Requirements

### Requirement: Blueprint defines ordered phases and substages
The Slice 8X blueprint MUST define an ordered path with at least these phases in the **chosen (deploy-first)** sequence: thin CI (7P.7 / 8X.1), finish remaining platform substages (7P.4–7P.6 and 7P.8 / 8X.4), a frontend pointer to the B-gate / frontend guide (8X.5), evaluation harness (8X.2), and HITL API-first on the existing agent surface (8X.3). Later substages MUST NOT be presented as prerequisites of earlier ones within the chosen sequence. The blueprint MAY document the alternate AI-depth-first order (CI → evals → HITL → finish prod → frontend) but MUST label it as alternate, not chosen.

#### Scenario: Phase order is unambiguous
- **GIVEN** the Slice 8X blueprint overview
- **WHEN** an implementer reads the chosen phase list
- **THEN** CI appears before finishing CD / 7P.8
- **AND** finishing CD / 7P.8 appears before the minimum frontend pointer
- **AND** the frontend pointer appears before eval harness work in the chosen sequence
- **AND** eval harness work appears before HITL API work in the chosen sequence

#### Scenario: Alternate depth-first path remains labeled
- **GIVEN** the Slice 8X blueprint path-divergence (or equivalent) section
- **WHEN** an implementer looks for the old CI → evals → HITL → prod spine
- **THEN** that order is present and explicitly marked alternate / AI-depth-first
- **AND** it is not presented as the active operator default

### Requirement: Blueprint states fallback boundaries and gate exception
The blueprint MUST document (1) what is explicitly out of scope for the 8X baseline, and (2) the intentional exception relative to “no feature work before 7P.8”: under the **chosen deploy-first** path, thin CI (7P.7 / 8X.1) is allowed before 7P.8; eval harness and HITL on `/ai/agent*` are sequenced **after** 7P.8 smoke (then frontend, then evals, then HITL) unless the operator explicitly switches to the alternate AI-depth-first path. GraphRAG, multi-agent-as-default, and new product domains remain blocked until the production gate passes. The blueprint MUST NOT authorize claiming a live production deployment before 7P.8 smoke succeeds.

#### Scenario: Allowed vs blocked before 7P.8 (deploy-first)
- **GIVEN** 7P.8 has not passed
- **AND** the operator is following the chosen deploy-first path
- **WHEN** an implementer consults the fallback / gate section
- **THEN** they can identify thin CI as allowed before 7P.8
- **AND** they are instructed that evals and HITL are deferred until after 7P.8 on the chosen path
- **AND** they can identify GraphRAG and multi-agent supervisor productization as blocked
- **AND** they are instructed not to claim production-live status without 7P.8 smoke

#### Scenario: HITL stays API-first in 8X.3
- **GIVEN** the HITL substage section
- **WHEN** an implementer reads the gate for that substage
- **THEN** success is defined with API/SSE (and script or curl) verification
- **AND** a polished frontend approval console is not required to pass that substage gate

### Requirement: Related docs cross-link Slice 8X
Canonical planning docs MUST point operators to `slice8_X.md` so the path is discoverable: at minimum `docs/documentation/blueprint/total.md`, `docs/documentation/blueprint/goal.md`, `docs/documentation/production.md`, and `docs/documentation/blueprint/slice-platform.md` MUST include a short pointer or gate-exception note referencing Slice 8X. Those pointers MUST describe the **chosen** sequence as CI → finish remaining 7P / 7P.8 → frontend → evals → HITL (deploy-first), and MUST NOT state that evals/HITL are required before 7P.8 on the default path.

#### Scenario: Operator finds 8X from platform tracker
- **GIVEN** an operator reading `production.md` or `slice-platform.md`
- **WHEN** they look for work order after 7P.0–7P.3
- **THEN** they are directed to Slice 8X for the deploy-first sequence
- **AND** the pointer does not instruct them to complete evals and HITL before finishing 7P.8 as the default

## ADDED Requirements

### Requirement: Blueprint readiness verdict starts at thin CI then platform finish
After 7P.0–7P.3 are complete, the Slice 8X blueprint readiness / verdict section MUST instruct the operator to start at thin CI inventory (`slice8_ci.md` §8X.1.0) and MUST state that the next major phase after CI on the chosen path is finishing platform substages (7P.4–7P.6, 7P.8), not the eval harness.

#### Scenario: Post-7P.3 next step is CI then finish prod
- **GIVEN** platform 7P.0–7P.3 are marked complete
- **WHEN** an operator reads the Slice 8X readiness verdict
- **THEN** they are told to open `slice8_ci.md` and start 8X.1.0
- **AND** they are told that after CI, chosen-path work continues with remaining 7P / 8X.4 before 8X.2 evals
