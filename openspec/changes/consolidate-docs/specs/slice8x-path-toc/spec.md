## ADDED Requirements

### Requirement: Ship-path index does not depend on slice8_X.md
The repository MUST NOT require `docs/documentation/blueprint/slice8_X.md` as a TOC that links to `slice8_ci.md`, `slice8_eval.md`, and `slice8_hitl.md`. Operator navigation MUST go through `docs/documentation/blueprint8.md` to surviving artifacts (`evals/README.md`, `docs/documentation/frontendguide.md`, `docs/documentation/production.md`).

#### Scenario: Operator does not need the old TOC
- **GIVEN** this change is complete
- **WHEN** an operator looks for CI, eval, or HITL operator docs
- **THEN** they can reach them from blueprint8 without opening `slice8_X.md`

## REMOVED Requirements

### Requirement: slice8_X.md is the TOC for detail blueprints
**Reason**: The Slice 8X split composer files are retired after those substages shipped.
**Migration**: Use `docs/documentation/blueprint8.md` as the index.

### Requirement: Path TOC keeps global laws and gate exception
**Reason**: Global laws and the pre-7P.8 exception narrative now live in blueprint8 (historical context) rather than a dedicated TOC file.
**Migration**: Read blueprint8 Alive law and remaining boxes in `goal.md`.
