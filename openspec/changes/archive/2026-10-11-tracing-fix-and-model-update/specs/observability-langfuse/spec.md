## ADDED Requirements

### Requirement: Hosted AI traces are named, closed, and filterable
When Langfuse is enabled, each `/ai/chat`, `/ai/chat/stream`, `/ai/agent`, and `/ai/agent/stream` turn MUST emit a root observation named `rag.answer` (chat) or `agent.turn` (agent). That observation MUST be ended when the turn finishes, including error and empty-retrieval exits, so operators see a non-empty name and a latency. Observations MUST carry an environment label and the service name `dashnote-api`. The environment label MUST default to `production` when debug is off and `development` when debug is on, and MUST honor an explicit operator override when set. Traces MUST NOT include API keys, tokens, or other secrets. A tracing failure MUST NOT fail the HTTP request. AI modules MUST NOT import the Langfuse SDK; enrichment stays in the observability layer.

#### Scenario: Chat trace is named and closed
- **GIVEN** Langfuse is enabled
- **WHEN** a client completes `POST /ai/chat/stream` with a valid JWT
- **THEN** Langfuse has a root observation named `rag.answer` with an end time and a latency
- **AND** the environment label and service name `dashnote-api` are set
- **AND** the response still succeeds if the tracing client later fails to flush

#### Scenario: Agent trace is distinguishable from chat
- **GIVEN** Langfuse is enabled
- **WHEN** a client completes `POST /ai/agent/stream` with a valid JWT
- **THEN** Langfuse has a root observation named `agent.turn` with an end time and a latency
- **AND** that observation is filterable by the same environment label and service name

#### Scenario: Production and laptop traces do not share one unlabeled bucket
- **GIVEN** one process runs with debug off and another with debug on
- **AND** neither sets an explicit environment override
- **WHEN** each process emits a chat trace
- **THEN** the debug-off trace is labeled `production`
- **AND** the debug-on trace is labeled `development`

### Requirement: RAG child spans include retrieval and context building
When Langfuse is enabled and a RAG turn searches the workspace, the trace MUST include a child span named `retrieval` that records retrieved chunk and/or note identities and scores (not counts only). When that turn builds a prompt from history and chunks, the trace MUST include a child span named `context_building`. The generation span MUST remain named `llm_generation` for chat or `call_model` for the agent loop. An empty retrieval MUST still close the `retrieval` span. These spans MUST be visible as separate observations, not only as fields buried on the generation.

#### Scenario: Successful chat exports the pre-generation spans
- **GIVEN** Langfuse is enabled
- **AND** the workspace search returns one or more chunks
- **WHEN** `POST /ai/chat/stream` finishes
- **THEN** the `rag.answer` trace contains child spans named `retrieval`, `context_building`, and `llm_generation`
- **AND** `retrieval` shows retrieved identities and scores

#### Scenario: Empty retrieval still closes retrieval
- **GIVEN** Langfuse is enabled
- **AND** the workspace search returns no chunks
- **WHEN** the chat turn returns the empty-retrieval answer
- **THEN** the `retrieval` span is ended
- **AND** the root `rag.answer` observation is ended

### Requirement: Streaming generations record time to first token
When Langfuse is enabled and a chat or agent response streams tokens, the generation observation MUST record time to first token measured until the first token is observed. Non-streaming completions are not required to set time to first token. Missing provider usage fields MUST NOT drop the generation or the parent trace.

#### Scenario: First streamed token sets time to first token
- **GIVEN** Langfuse is enabled
- **WHEN** `POST /ai/chat/stream` yields at least one token
- **THEN** the `llm_generation` observation has a time-to-first-token value
- **AND** the parent `rag.answer` observation is still closed with a latency

### Requirement: Soft health reports Langfuse without becoming a deploy gate
`GET /health/ai` MUST include whether Langfuse is enabled (both keys non-empty) and the effective host, and MUST NOT include key material. Missing keys or a failed client MUST NOT change `GET /health` and MUST NOT by themselves mark `GET /health/ai` unavailable. `GET /health` MUST continue to reflect only Postgres and Redis.

#### Scenario: Keys present
- **GIVEN** both Langfuse keys are set
- **WHEN** a client calls `GET /health/ai`
- **THEN** the body reports Langfuse as enabled
- **AND** the body does not contain the secret key or public key

#### Scenario: Keys absent do not fail hard health
- **GIVEN** Langfuse keys are empty
- **WHEN** a client calls `GET /health` and `GET /health/ai`
- **THEN** `GET /health` is unchanged
- **AND** `GET /health/ai` reports Langfuse as disabled
