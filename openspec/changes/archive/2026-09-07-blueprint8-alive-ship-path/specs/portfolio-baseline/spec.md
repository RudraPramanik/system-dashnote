## ADDED Requirements

### Requirement: Ship-plan locks hiring path to blueprint8
`docs/ship-plan.md` MUST identify `docs/documentation/blueprint8.md` as the locked ship path for top-~10% (job gate) and top-~3–5% (Tier 1/2 deepeners). Day/phase checklists in ship-plan MUST NOT instruct operators to follow a contradictory default order.

#### Scenario: Ship-plan reader sees locked path
- **GIVEN** this change is complete
- **WHEN** a reader opens `docs/ship-plan.md`
- **THEN** they find an explicit lock/pointer to blueprint8
- **AND** Phase 2 depth items include HITL, Langfuse-depth evals, and measure→improve experiments consistent with blueprint8

### Requirement: Portfolio claims stay honest under Alive law
Portfolio packaging docs updated by this path MUST continue to forbid claiming live production or “production-ready” without smoke/live evidence, and MUST distinguish Tier 0 job-gate metrics from optional Tier 2 lab metrics.

#### Scenario: Metrics distinguish gate vs lab
- **GIVEN** README or ship-plan metrics sections after this change
- **WHEN** a reader looks for quality signals
- **THEN** eval pass-rate / cost-latency remain the job-gate signals
- **AND** any recall@k or faithfulness figures are labeled optional/nightly or pending when not measured
