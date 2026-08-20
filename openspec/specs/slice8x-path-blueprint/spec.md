## Purpose

Slice 8X path planning blueprint (`slice8_X.md`): chosen deploy-first ship path (CI → finish-prod → frontend → evals → HITL), with alternate AI-depth-first order, laws, gates, and narrowed pre-7P.8 exception (thin CI only before 7P.8 on the chosen path).

## Requirements

### Requirement: Slice 8X blueprint document exists
The repository MUST include `docs/documentation/blueprint/slice8_X.md` as the executable planning blueprint for the Slice 8X ship path (chosen deploy-first sequence). The document MUST be usable as a Cursor Composer guideline (architecture law block + per-substage objective prompts), not merely a high-level essay.

#### Scenario: Operator opens the blueprint
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/documentation/blueprint/slice8_X.md`
- **THEN** the file is non-empty
- **AND** it identifies itself as Slice 8X (distinct from GraphRAG Slice 8 and multi-agent Slice 9)

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

### Requirement: Blueprint includes architecture laws and Composer prompts
The blueprint MUST include a paste-first architecture law block for 8X sessions and, for each build substage, a concrete objective-style prompt (goal, constraints/laws, validation gate). Prompts MUST forbid breaking local `docker compose` and MUST preserve chat≠agent coexistence (`/ai/chat*` and `/ai/agent*` both remain).

#### Scenario: Composer session can start from the law block
- **GIVEN** an implementer begins a substage
- **WHEN** they paste the 8X architecture law and the substage objective prompt
- **THEN** the prompt states not to break the local full-stack compose path
- **AND** states not to replace chat routes with agent routes

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

### Requirement: Blueprint specifies minimum eval and HITL expectations
The blueprint MUST require the eval phase to cover retrieval relevance, tenant isolation, and at least five agent trajectory cases (including forbid surprise note creation). The HITL phase MUST describe interrupt-before-mutation and resume-by-thread semantics for create/update tool paths, with workspace/user/role continuing to come from trusted request/graph state (not model-invented tenant fields).

#### Scenario: Eval minimum themes listed
- **GIVEN** the eval substage in the blueprint
- **WHEN** an implementer plans the golden corpus
- **THEN** retrieval, tenant isolation, and ≥5 agent trajectory cases are listed as required themes

#### Scenario: HITL mutation gate described
- **GIVEN** the HITL substage in the blueprint
- **WHEN** an implementer designs interrupt points
- **THEN** create_note and update_note (or equivalent mutation tools) require approval before side effects
- **AND** resume is keyed by checkpoint/thread identity already used by the agent

### Requirement: Related docs cross-link Slice 8X
Canonical planning docs MUST point operators to `slice8_X.md` so the path is discoverable: at minimum `docs/documentation/blueprint/total.md`, `docs/documentation/blueprint/goal.md`, `docs/documentation/production.md`, and `docs/documentation/blueprint/slice-platform.md` MUST include a short pointer or gate-exception note referencing Slice 8X. Those pointers MUST describe the **chosen** sequence as CI → finish remaining 7P / 7P.8 → frontend → evals → HITL (deploy-first), and MUST NOT state that evals/HITL are required before 7P.8 on the default path.

#### Scenario: Operator finds 8X from platform tracker
- **GIVEN** an operator reading `production.md` or `slice-platform.md`
- **WHEN** they look for work order after 7P.0–7P.3
- **THEN** they are directed to Slice 8X for the deploy-first sequence
- **AND** the pointer does not instruct them to complete evals and HITL before finishing 7P.8 as the default

### Requirement: Blueprint readiness verdict starts at thin CI then platform finish
After 7P.0–7P.3 are complete, the Slice 8X blueprint readiness / verdict section MUST instruct the operator to start at thin CI inventory (`slice8_ci.md` §8X.1.0) and MUST state that the next major phase after CI on the chosen path is finishing platform substages (7P.4–7P.6, 7P.8), not the eval harness.

#### Scenario: Post-7P.3 next step is CI then finish prod
- **GIVEN** platform 7P.0–7P.3 are marked complete
- **WHEN** an operator reads the Slice 8X readiness verdict
- **THEN** they are told to open `slice8_ci.md` and start 8X.1.0
- **AND** they are told that after CI, chosen-path work continues with remaining 7P / 8X.4 before 8X.2 evals
