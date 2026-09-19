## ADDED Requirements

### Requirement: Production-shaped Langfuse env enables the client
Langfuse MUST be treated as enabled when both the public key and secret key are non-empty. The host MUST be taken from `LANGFUSE_HOST` when set, and MUST accept `LANGFUSE_BASE_URL` as an alias when `LANGFUSE_HOST` is unset or blank so production-shaped env files enable the same cloud project. Operator and production example docs MUST name these variables and MUST NOT require pasting live key values into the repository.

#### Scenario: BASE_URL alias enables tracing
- **GIVEN** `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set
- **AND** `LANGFUSE_HOST` is blank
- **AND** `LANGFUSE_BASE_URL` is a Langfuse cloud URL
- **WHEN** the API initializes the Langfuse client
- **THEN** tracing is treated as enabled
- **AND** the client uses that host

#### Scenario: Documented HOST still works
- **GIVEN** `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` are set
- **WHEN** the API initializes the Langfuse client
- **THEN** tracing is treated as enabled
- **AND** the client uses `LANGFUSE_HOST`

### Requirement: Serving path never awaits a Langfuse judge
When Langfuse is enabled, chat and agent requests MAY emit traces and attach empty-retrieval or user-feedback scores after the turn. The HTTP or stream response for `/ai/chat` and `/ai/agent` MUST NOT wait for an LLM-as-judge or sampled faithfulness job to finish. When Langfuse is disabled or the client fails, those routes MUST still succeed.

#### Scenario: Chat returns without a judge hop
- **GIVEN** Langfuse is enabled
- **WHEN** a client calls `/ai/chat` or `/ai/agent`
- **THEN** the response is produced without awaiting a faithfulness or GEval completion
- **AND** a parent observation (`rag.answer` or `agent.turn`) is emitted when the client is healthy

#### Scenario: Disabled tracing does not fail the request
- **GIVEN** Langfuse keys are missing or the client fails to initialize
- **WHEN** RAG chat or an agent turn runs
- **THEN** the HTTP/graph path still succeeds
- **AND** missing tracing MUST NOT crash the API

### Requirement: Quality events stay low-cardinality on Prometheus
The API MUST keep exposing low-cardinality counters on `/metrics` for empty retrieval, agent HITL interrupt, and LLM fallback. Counters MUST NOT include unbounded labels (no raw question text, no user id as a label). Per-trace Langfuse scores and user thumbs MUST NOT be exported as Prometheus judge series.

#### Scenario: Metrics still include AI quality counters
- **GIVEN** this change is complete
- **WHEN** an operator scrapes `/metrics` after AI traffic
- **THEN** the documented `dashnote_ai_*` quality counters are present
- **AND** `dashnote_api_http_requests_total` still records HTTP requests

#### Scenario: Thumbs stay off Prometheus
- **GIVEN** a user-feedback score exists on a Langfuse trace
- **WHEN** an operator scrapes `/metrics`
- **THEN** they MUST NOT find per-trace or per-user thumbs/judge score series from this change
