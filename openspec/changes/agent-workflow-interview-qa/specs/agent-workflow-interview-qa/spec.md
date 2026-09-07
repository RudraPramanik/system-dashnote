## Purpose

Production-level AI agent, workflow, and automation interview Q&A at `docs/documentation/qs3.md` for concept clearance and hire loops, complementary to `qs2.md` (RAG/production AI) and `qs.md` (this repo).

## ADDED Requirements

### Requirement: Interview Q&A document exists as an agent-workflow gate
The repository SHALL provide a production agent/workflow/automation interview Q&A document at `docs/documentation/qs3.md` that a candidate can use both to pass hiring loops and to verify they understand workflows vs agents, the five core workflow patterns, and plan/reflect/tool/orchestration fundamentals.

#### Scenario: File is present, navigable, and non-empty
- **WHEN** a reader opens `docs/documentation/qs3.md`
- **THEN** the file MUST contain a title, purpose statement, table of contents, mermaid diagrams at major sections, and substantive Q&A
- **AND** the document MUST state that length is expected and completeness is preferred over brevity

#### Scenario: Dual use as interview and concept gate
- **WHEN** a reader studies a question
- **THEN** the answer MUST be usable as a spoken interview response
- **AND** the same answer MUST include mechanism, tradeoff, and failure-mode depth for a follow-up probe

### Requirement: qs3 complements qs2 and qs.md without duplicating them
`qs3.md` SHALL cover agents, workflows, and automations in depth. Topics already taught in `qs2.md` (RAG pipelines, embeddings, vector DBs, enterprise RAG-on-DB, TTFT/E2E, tenant filters from identity, RAG goldens, chat-vs-agent coexistence at the product-API level) MUST be referenced to `qs2.md` rather than rewritten. `qs.md` remains the DashNoteSystem-specific talk track.

#### Scenario: Reader finds the three tracks
- **WHEN** a reader opens `qs3.md`
- **THEN** they MUST see explicit pointers to `qs2.md` and `qs.md`
- **AND** `qs2.md` MUST gain a pointer to `qs3.md` for the agent/workflow track

#### Scenario: Overlap is a pointer, not a second essay
- **WHEN** an answer needs RAG, tenancy filters, embedding lag, or chat-vs-agent product coexistence
- **THEN** the answer MUST point to the relevant `qs2.md` section instead of repeating that section’s content
- **AND** `qs3.md` MUST still add agent-specific depth (for example: retrieval as a tool, trajectory evals, graph interrupts) that `qs2.md` does not teach

### Requirement: Five core workflow patterns are first-class
The document SHALL teach the five production workflow patterns as named, drawable patterns: prompt chaining, routing, parallelization, orchestrator-workers, and evaluator-optimizer — plus when to use a compiled workflow instead of an autonomous agent.

#### Scenario: Each of the five patterns has Q&A
- **WHEN** an interviewer asks what the five core agent/workflow patterns are, or asks about chaining, routing, parallelization, orchestrator-workers, or evaluator-optimizer
- **THEN** the document MUST define each pattern, when it wins, and a failure mode
- **AND** each pattern MUST have a mermaid diagram or share a diagram that makes the dataflow obvious

#### Scenario: Workflow vs agent is explicit
- **WHEN** an interviewer asks “workflow or agent?”
- **THEN** the document MUST state that predetermined LLM pipelines (workflows) are the default when the path is known, and autonomous tool loops (agents) are for unknown steps
- **AND** it MUST NOT claim “always use an agent”

### Requirement: Plan, reflection, tools, and orchestration are covered
The document SHALL cover plan-and-execute (and related plan/act splits), reflection/self-critique, tool use and function calling, and orchestration (graphs, queues, durable execution) as interview-ready fundamentals.

#### Scenario: Tool and function-calling answers exist
- **WHEN** an interviewer asks how tool/function calling works in production
- **THEN** the document MUST cover schemas, validation, identity-scoped execution, parallel tool calls, idempotency, and blast radius
- **AND** it MUST distinguish provider function-calling from letting the model emit raw SQL or shell

#### Scenario: Plan-execute and reflection answers exist
- **WHEN** an interviewer asks about planning, ReAct, plan-and-execute, or reflection
- **THEN** the document MUST compare those control loops and say when a compiled graph beats free-form ReAct
- **AND** it MUST describe reflection as an eval/critique step with a stop condition, not an unbounded inner monologue

#### Scenario: Orchestration and automation answers exist
- **WHEN** an interviewer asks how to run agents as production automations
- **THEN** the document MUST cover orchestration (graphs vs queues vs durable workflows), background vs interactive agents, retries, HITL interrupts, and why LLM steps sit inside a deterministic job runner

### Requirement: Missed hire-loop topics beyond qs2 are present
The document SHALL include additional production topics that `qs2.md` omitted or only named: multi-agent patterns, context compaction for long runs, sandboxed code execution, MCP-style tool servers, agent trajectory evals, deterministic vs LLM steps in a workflow, and when not to use an agent.

#### Scenario: Multi-agent and “when not to” are interview-ready
- **WHEN** an interviewer asks about multi-agent systems or why not to add more agents
- **THEN** the document MUST cover supervisor/handoff patterns, extra latency/cost, and a default of one agent plus tools unless roles are truly distinct

#### Scenario: Counter-questions exist
- **WHEN** a reader prepares for pushback
- **THEN** the document MUST include a counter-question section covering at least workflow vs agent, ReAct vs graph, and multi-agent vs one agent with tools
