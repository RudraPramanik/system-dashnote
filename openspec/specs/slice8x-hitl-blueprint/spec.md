## Purpose

Slice 8X HITL detail blueprint (`slice8_hitl.md`): multi-substep Cursor prompts for API-first human-in-the-loop on agent mutations (8X.3).

## Requirements

### Requirement: Slice 8X HITL detail blueprint exists
The repository MUST include `docs/documentation/blueprint/slice8_hitl.md` as the executable multi-substep blueprint for API-first human-in-the-loop on agent mutations (Slice 8X.3). The document MUST be Cursor-ready with paste-first laws and per-substep objective prompts.

#### Scenario: Operator opens HITL blueprint
- **GIVEN** this change is complete
- **WHEN** an operator opens `slice8_hitl.md`
- **THEN** the file is non-empty
- **AND** it identifies itself as the detail blueprint for 8X.3 / HITL
- **AND** it links back to `slice8_X.md`

### Requirement: HITL blueprint defines ordered substages
The HITL blueprint MUST define ordered substages covering at least: interrupt before create/update note tool side effects, SSE (or stream) approval event aligned with existing agent stream shapes, resume by thread/checkpoint identity, and script/curl plus automated tests proving approve vs reject. A polished frontend approval console MUST NOT be required to pass the HITL blueprint gate.

#### Scenario: API-first gate
- **GIVEN** the HITL final gate section
- **WHEN** an implementer checks completion criteria
- **THEN** success is defined via API/SSE and script or curl verification
- **AND** Next.js approval UI is explicitly out of scope for that gate

### Requirement: HITL blueprint preserves chat coexistence and tenant freeze
HITL prompts MUST forbid modifying `/ai/chat*` as a replacement path, MUST keep tools on the service layer, and MUST require workspace/user/role from trusted graph/request state (not model-overridable tenant fields).

#### Scenario: Chat untouched and tenant frozen
- **GIVEN** the HITL architecture law
- **WHEN** an implementer starts the interrupt substep
- **THEN** they are instructed not to replace chat routes
- **AND** they are instructed that tenant fields come from trusted state only
