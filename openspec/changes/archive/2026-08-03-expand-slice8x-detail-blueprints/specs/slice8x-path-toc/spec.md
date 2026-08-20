## ADDED Requirements

### Requirement: slice8_X.md is the TOC for detail blueprints
`docs/documentation/blueprint/slice8_X.md` MUST remain the entry index for the Slice 8X ship path and MUST direct implementers to `slice8_ci.md` for 8X.1, `slice8_eval.md` for 8X.2, and `slice8_hitl.md` for 8X.3. It MUST NOT be the only place that holds full multi-substep Composer task bodies for those three phases once the detail files are authored.

#### Scenario: Index points to split files
- **GIVEN** this change is complete
- **WHEN** an operator reads the 8X.1–8X.3 sections of `slice8_X.md`
- **THEN** each section links to the corresponding detail blueprint file
- **AND** the locked order CI → evals → HITL → finish prod → frontend remains visible

### Requirement: Path TOC keeps global laws and gate exception
The TOC document MUST continue to document the global Slice 8X architecture law summary (or point to it), the intentional pre-7P.8 exception (CI/evals/HITL allowed; GraphRAG/multi-agent blocked), and pointers for 8X.4 (`slice-platform.md`) and 8X.5 (`frontendguide.md` / B-gate).

#### Scenario: Exception still discoverable from TOC
- **GIVEN** an operator opens `slice8_X.md`
- **WHEN** they look for what may run before 7P.8
- **THEN** they can identify CI, evals, and HITL API as allowed
- **AND** they can identify GraphRAG and multi-agent productization as blocked
