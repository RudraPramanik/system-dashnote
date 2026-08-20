## ADDED Requirements

### Requirement: HITL blueprint requires LangGraph interrupt API discipline
The HITL blueprint MUST instruct implementers to read the installed LangGraph version and existing graph code before choosing an interrupt API, and MUST note that `langgraph>=0.1.0` is too loose to assume a single interrupt style. When implementing, the blueprint MUST prefer tightening the version pin to the API actually used rather than guessing across major interrupt redesigns.

#### Scenario: Version check before interrupt code
- **GIVEN** substep 8X.3.1
- **WHEN** an implementer adds interrupt-before-mutation
- **THEN** they are instructed to verify the installed LangGraph interrupt API first
- **AND** not invent a second persistence system when the checkpointer can hold interrupt state

### Requirement: HITL blueprint requires resume tenant ownership validation
The HITL blueprint MUST require that resume/reject endpoints re-validate that the `thread_id` (and associated checkpoint) belongs to the authenticated caller’s workspace before resuming. Trusted graph state alone is insufficient if the client can present an arbitrary thread id.

#### Scenario: Cross-tenant resume is rejected
- **GIVEN** a resume request with a thread_id from another workspace
- **WHEN** the resume path runs authorization checks described in the blueprint
- **THEN** the blueprint requires denial / no mutation
- **AND** workspace_id continues to come from trusted auth context, not model args

### Requirement: HITL blueprint locks SSE interrupt lifecycle and event shape
The HITL blueprint MUST lock the `approval_required` (or confirmed name) JSON fields to at least: type, tool, args (or args summary), thread_id, and interrupt/resume id. It MUST specify stream lifecycle after interrupt—preferred default: emit `approval_required` then end the SSE stream; client uses resume API with the same thread_id (reconnect). It MUST document ordering relative to existing `tool_start` / `tool_end` / `done` / `error` events from `ai_routes/agent.py`.

#### Scenario: Client can parse approval_required
- **GIVEN** the proposed stream contract in the blueprint
- **WHEN** a streaming client receives an interrupt
- **THEN** the event shape is explicit enough to parse without guessing keys
- **AND** the lifecycle (close vs keep-open) is stated so clients know whether to reconnect

### Requirement: HITL blueprint clarifies checkpointer vs automation pending queue
The HITL blueprint MUST state that agent HITL pending state for this gate lives in the existing LangGraph checkpointer + thread_id, and MUST NOT require a new `pending_actions` table solely for 8X.3. Slice 7 `AutomationDecisionEngine` / automation review queue is a different surface and MUST NOT be conflated as a mandatory dependency for agent mutation HITL.

#### Scenario: No mandatory second pending table
- **GIVEN** the HITL architecture law
- **WHEN** an implementer designs interrupt persistence
- **THEN** they reuse the checkpointer
- **AND** they are told not to invent a second persistence system for this gate

## MODIFIED Requirements

### Requirement: HITL blueprint defines ordered substages
The HITL blueprint MUST define ordered substages covering at least: interrupt before create/update note tool side effects (with LangGraph API discipline), SSE (or stream) approval event with locked shape and lifecycle, resume by thread/checkpoint identity with workspace ownership validation, and script/curl plus automated tests proving approve vs reject. A polished frontend approval console MUST NOT be required to pass the HITL blueprint gate.

#### Scenario: API-first gate
- **GIVEN** the HITL final gate section
- **WHEN** an implementer checks completion criteria
- **THEN** success is defined via API/SSE and script or curl verification
- **AND** Next.js approval UI is explicitly out of scope for that gate

#### Scenario: Resume validates workspace
- **GIVEN** the resume substep
- **WHEN** approval continues a mutation
- **THEN** the blueprint requires tenant ownership checks on the thread before side effects proceed
