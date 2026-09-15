## ADDED Requirements

### Requirement: Tracing facade supports parent and child observations for all AI surfaces
When Langfuse is enabled, the observability layer MUST allow AI request paths to open a named parent observation and child spans (including generation-typed LLM calls) without importing the Langfuse SDK in application AI modules. Existing RAG helper names MUST remain usable as aliases so `/ai/chat*` tracing does not require a caller rewrite.

#### Scenario: RAG callers keep working via aliases
- **GIVEN** Langfuse is enabled
- **WHEN** a `/ai/chat` or `/ai/chat/stream` request completes a RAG answer
- **THEN** a parent observation named `rag.answer` is still produced with retrieval identities/scores on the retrieval span when chunks exist
- **AND** application AI modules still MUST NOT import the Langfuse SDK directly

#### Scenario: Disabled tracing does not fail the request
- **GIVEN** Langfuse is not configured or disabled
- **WHEN** RAG chat or an agent turn runs
- **THEN** the HTTP/graph path still succeeds
- **AND** missing tracing MUST NOT crash the API or agent path

### Requirement: Agent turns are first-class traces
When Langfuse is enabled, each `/ai/agent`, `/ai/agent/stream`, `/ai/agent/resume`, and `/ai/agent/reject` invocation MUST emit a parent observation named `agent.turn` with metadata including `workspace_id`, `user_id`, and `role` from JWT context (never a raw JWT). Child observations MUST cover the planner LLM hop (`call_model`) as a generation and named tool executions when tools run. HITL pause MUST be visible as an interrupt-related span or score. Existing agent request and response shapes (including `approval_required`) MUST remain unchanged.

#### Scenario: Completed agent turn has a planner generation
- **GIVEN** Langfuse is enabled
- **AND** a user invokes `/ai/agent` with a message that completes without interrupt
- **WHEN** an operator inspects the resulting trace
- **THEN** they find a parent named `agent.turn`
- **AND** a generation-typed child for the planner model call
- **AND** the JSON response still includes `status`, `answer`, `thread_id`, `steps_taken`, and `tool_calls_made` as today

#### Scenario: HITL interrupt is visible without changing the SSE contract
- **GIVEN** Langfuse is enabled
- **AND** the agent hits a mutation interrupt
- **WHEN** the stream or non-stream response returns `approval_required`
- **THEN** the `agent.turn` trace records the interrupt (span and/or score)
- **AND** the existing HITL event payload fields remain valid for clients

### Requirement: Nested RAG attaches under the agent parent
When an agent tool invokes RAG answer while an `agent.turn` parent is active and Langfuse is enabled, the resulting `rag.answer` observation MUST be a child of that parent, not a disconnected sibling trace. Direct `/ai/chat*` RAG (no agent parent) MUST still open a standalone `rag.answer` root as today.

#### Scenario: Search tool RAG is nested
- **GIVEN** Langfuse is enabled
- **AND** an agent turn calls the notes search or summarize tool
- **WHEN** that tool runs RAG answer
- **THEN** the `rag.answer` tree is nested under the same `agent.turn` parent
- **AND** retrieval identities and scores still appear on the retrieval span when chunks exist

#### Scenario: Direct chat RAG stays a root
- **GIVEN** Langfuse is enabled
- **AND** no agent parent is active
- **WHEN** `/ai/chat` runs
- **THEN** `rag.answer` remains a root observation (not required to sit under `agent.turn`)

### Requirement: Known quality events increment Prometheus counters
The API MUST expose low-cardinality counters on `/metrics` for empty retrieval, agent HITL interrupt, and LLM fallback. Counters MUST NOT include unbounded labels (no raw question text, no user id as a label). Token cost and LLM-as-judge numeric scores MUST NOT be exported as Prometheus series in this change. Existing HTTP instrumentator metrics (`dashnote_api_*`) MUST remain.

#### Scenario: Empty retrieval increments a counter
- **GIVEN** a RAG answer path retrieves zero chunks
- **WHEN** `/metrics` is scraped after the request
- **THEN** an empty-retrieval counter has increased
- **AND** `dashnote_api_http_requests_total` still records the HTTP request

#### Scenario: Judge scores stay off Prometheus
- **GIVEN** a faithfulness judge score exists on a Langfuse trace
- **WHEN** an operator scrapes `/metrics`
- **THEN** they MUST NOT find per-trace or per-user judge score series from this change
