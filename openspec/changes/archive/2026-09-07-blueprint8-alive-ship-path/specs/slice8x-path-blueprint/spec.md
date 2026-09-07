## ADDED Requirements

### Requirement: Blueprint8 is operator-default over Slice 8X index
Canonical planning docs MUST treat `docs/documentation/blueprint8.md` as the operator-default ship path. `docs/documentation/blueprint/slice8_X.md` MUST remain the detail index for Slice 8X substages and MUST NOT contradict blueprint8’s Alive law or Tier 0→1→2 map. Cross-links in `total.md`, `goal.md`, `production.md`, and `slice-platform.md` MUST point operators to blueprint8 first, then to Slice 8X detail docs for executable prompts.

#### Scenario: Operator finds default path from platform tracker
- **GIVEN** an operator reading `production.md` or `goal.md` after this change
- **WHEN** they look for the locked ship order
- **THEN** they are directed to `blueprint8.md` as the default
- **AND** they can still reach `slice8_X.md` / detail blueprints for Composer substages

#### Scenario: Slice 8X chosen sequence remains deploy-first compatible
- **GIVEN** blueprint8 and `slice8_X.md` both exist
- **WHEN** an implementer compares default sequences
- **THEN** neither document requires GraphRAG productization before the job gate
- **AND** chat≠agent coexistence remains required
