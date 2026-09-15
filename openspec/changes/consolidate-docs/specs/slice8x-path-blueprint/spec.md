## ADDED Requirements

### Requirement: Operators follow blueprint8 instead of Slice 8X composer files
Operators MUST be directed to `docs/documentation/blueprint8.md` (law) and `docs/documentation/blueprint/goal.md` (checkboxes) for the ship path. The repository MUST NOT require `docs/documentation/blueprint/slice8_X.md` to exist as a live Composer planning blueprint. Chat≠agent coexistence and GraphRAG-as-non-goal MUST remain as documented in blueprint8.

#### Scenario: Operator finds the ship path without slice8_X
- **GIVEN** this change is complete
- **WHEN** an operator looks for the locked ship order
- **THEN** they are directed to `blueprint8.md`
- **AND** they are not required to open `slice8_X.md`

## REMOVED Requirements

### Requirement: Slice 8X blueprint document exists
**Reason**: Historical Composer planning file; the ship path now lives in blueprint8 + goal.md.
**Migration**: Use `docs/documentation/blueprint8.md` and `docs/documentation/blueprint/goal.md`.

### Requirement: Blueprint defines ordered phases and substages
**Reason**: Phase order is owned by blueprint8; the Slice 8X composer file is retired.
**Migration**: Follow blueprint8 Tier 0 then Tier 1/2 map.

### Requirement: Blueprint includes architecture laws and Composer prompts
**Reason**: Paste-first Composer prompts for already-shipped substages are no longer maintained.
**Migration**: Use canonical docs (`system.md`, `ai.md`, `rules.md`) and OpenSpec apply for new work.

### Requirement: Blueprint states fallback boundaries and gate exception
**Reason**: Alive / gate rules are stated in blueprint8.
**Migration**: Read blueprint8 Alive law and job-gate spine.

### Requirement: Blueprint specifies minimum eval and HITL expectations
**Reason**: Eval and HITL minima live in `ai-eval-harness`, `evals/README.md`, and `frontendguide.md` / `ai.md`.
**Migration**: Use those shipped operator docs.

### Requirement: Related docs cross-link Slice 8X
**Reason**: Cross-links to a retired index would 404.
**Migration**: Point `goal.md` and `production.md` at blueprint8.

### Requirement: Blueprint readiness verdict starts at thin CI then platform finish
**Reason**: Verdict text lived in the retired Slice 8X file; CI and platform work already shipped.
**Migration**: Track remaining ops boxes in `goal.md` / `production.md` / `devops-progress.md`.

### Requirement: Blueprint8 is operator-default over Slice 8X index
**Reason**: With Slice 8X files gone, blueprint8 is the only ship-path index.
**Migration**: Keep blueprint8 as the default; do not retain a `slice8_X.md` dual index.
