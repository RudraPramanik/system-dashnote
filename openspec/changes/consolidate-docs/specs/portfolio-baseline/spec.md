## MODIFIED Requirements

### Requirement: Architecture discoverability
README MUST link to existing system/AI documentation (e.g. `docs/documentation/system.md`, `docs/documentation/ai.md`, and/or UML docs) so reviewers can navigate tenancy and AI laws without hunting the tree. Every link in the README Documentation section MUST resolve to a file that exists after consolidation.

#### Scenario: Architecture links resolve
- **GIVEN** the updated root README
- **WHEN** a reader follows the architecture documentation links
- **THEN** they reach in-repo docs that describe routing/tenancy and AI behavior

#### Scenario: Documentation index has no dead paths
- **GIVEN** consolidation is complete
- **WHEN** a reader follows each README Documentation link
- **THEN** the target file exists
- **AND** the index does not list `docs/ship-plan.md` or deleted `blueprint/slice*.md` files as current

### Requirement: Portfolio claims stay honest under Alive law
Portfolio packaging docs updated by this path MUST continue to forbid claiming live production or “production-ready” without smoke/live evidence, and MUST distinguish Tier 0 job-gate metrics from optional Tier 2 lab metrics.

#### Scenario: Metrics distinguish gate vs lab
- **GIVEN** README or goal.md metrics sections after this change
- **WHEN** a reader looks for quality signals
- **THEN** eval pass-rate / cost-latency remain the job-gate signals
- **AND** any recall@k or faithfulness figures are labeled optional/nightly or pending when not measured

## ADDED Requirements

### Requirement: Goal tracker locks hiring path to blueprint8
`docs/documentation/blueprint/goal.md` MUST identify `docs/documentation/blueprint8.md` as the locked ship path for top-~10% (job gate) and top-~3–5% (Tier 1/2 deepeners). Checklists in goal.md MUST NOT instruct operators to follow a contradictory default order.

#### Scenario: Goal tracker reader sees locked path
- **GIVEN** this change is complete
- **WHEN** a reader opens `docs/documentation/blueprint/goal.md`
- **THEN** they find an explicit lock/pointer to blueprint8
- **AND** remaining depth items include HITL, Langfuse-depth evals, and measure→improve experiments consistent with blueprint8

## REMOVED Requirements

### Requirement: Ship-plan locks hiring path to blueprint8
**Reason**: Hiring-path lock belongs on blueprint8 + goal.md; `docs/ship-plan.md` is deleted as a duplicate tracker.
**Migration**: Read `docs/documentation/blueprint8.md` and `docs/documentation/blueprint/goal.md`.
