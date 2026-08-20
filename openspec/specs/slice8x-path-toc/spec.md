## Purpose

Slice 8X path TOC role for `slice8_X.md`: index linking to CI/eval/HITL detail blueprints while preserving global laws and the chosen deploy-first pre-7P.8 exception (thin CI allowed; evals/HITL deferred until after 7P.8).

## Requirements

### Requirement: slice8_X.md is the TOC for detail blueprints
`docs/documentation/blueprint/slice8_X.md` MUST remain the entry index for the Slice 8X ship path and MUST direct implementers to `slice8_ci.md` for 8X.1, `slice8_eval.md` for 8X.2, and `slice8_hitl.md` for 8X.3. It MUST NOT be the only place that holds full multi-substep Composer task bodies for those three phases once the detail files are authored. The TOC MUST present the **chosen** locked order as CI → finish prod (8X.4) → frontend (8X.5) → evals (8X.2) → HITL (8X.3), while still linking the same detail files.

#### Scenario: Index points to split files
- **GIVEN** this change is complete
- **WHEN** an operator reads the 8X.1–8X.3 sections of `slice8_X.md`
- **THEN** each section links to the corresponding detail blueprint file
- **AND** the chosen locked order CI → finish prod → frontend → evals → HITL remains visible

### Requirement: Path TOC keeps global laws and gate exception
The TOC document MUST continue to document the global Slice 8X architecture law summary (or point to it), the intentional pre-7P.8 exception under the **chosen deploy-first** path (thin CI allowed before 7P.8; evals and HITL deferred until after 7P.8 smoke on the default path; GraphRAG/multi-agent blocked until 7P.8), and pointers for 8X.4 (`slice-platform.md`) and 8X.5 (`frontendguide.md` / B-gate).

#### Scenario: Exception still discoverable from TOC
- **GIVEN** an operator opens `slice8_X.md`
- **WHEN** they look for what may run before 7P.8 on the chosen path
- **THEN** they can identify thin CI as allowed
- **AND** they can identify evals and HITL as deferred until after 7P.8 on the chosen path
- **AND** they can identify GraphRAG and multi-agent productization as blocked
