## ADDED Requirements

### Requirement: HITL operator truth is live AI and frontend docs
Operators MUST find agent HITL (approval_required, resume, reject) in `docs/documentation/ai.md` and `docs/documentation/frontendguide.md`. The repository MUST NOT require `docs/documentation/blueprint/slice8_hitl.md` to exist.

#### Scenario: Operator does not need slice8_hitl.md
- **GIVEN** this change is complete
- **WHEN** an operator or frontend implementer looks up HITL
- **THEN** they can follow `ai.md` and `frontendguide.md`
- **AND** they are not required to open `slice8_hitl.md`

## REMOVED Requirements

### Requirement: Slice 8X HITL detail blueprint exists
**Reason**: HITL already shipped on `/ai/agent*`; the Composer prompt file is leftover.
**Migration**: Use `docs/documentation/ai.md`, `frontendguide.md`, and the `agent-hitl` spec.

### Requirement: HITL blueprint defines ordered substages
**Reason**: Interrupt/resume behavior is live; substages are complete.
**Migration**: Change HITL via `agent-hitl`, not a restored prompt file.

### Requirement: HITL blueprint preserves chat coexistence and tenant freeze
**Reason**: Chat≠agent and JWT tenancy remain in canonical AI/frontend docs.
**Migration**: Follow `ai.md` and `frontendguide.md`.

### Requirement: HITL blueprint requires LangGraph interrupt API discipline
**Reason**: Live agent contract is documented in `ai.md` / `agent-hitl`.
**Migration**: Use those docs/specs.

### Requirement: HITL blueprint requires resume tenant ownership validation
**Reason**: Tenant freeze on resume/reject remains a live API law.
**Migration**: `frontendguide.md` and `agent-hitl` remain authoritative.

### Requirement: HITL blueprint locks SSE interrupt lifecycle and event shape
**Reason**: SSE event shape is documented in `frontendguide.md` / `ai.md`.
**Migration**: Use those surviving docs.

### Requirement: HITL blueprint clarifies checkpointer vs automation pending queue
**Reason**: Distinguishing graph interrupt from automation governance is covered in canonical AI/LLD docs as needed.
**Migration**: Read `ai.md` / `lld.md`; do not restore `slice8_hitl.md`.
