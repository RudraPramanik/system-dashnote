## Purpose

Server-binds workspace, user, and role for LangGraph agent tools so model-supplied tenant fields cannot select another tenant’s notes or bypass session identity.

## Requirements

### Requirement: HarnessContext is built from the authenticated request
For each `/ai/agent*` invoke, the system MUST construct a trusted harness context from the JWT-derived request context (`workspace_id`, `user_id`, `role`) and MUST make that context available for the duration of the graph invoke (including tool execution). Trace and remaining-budget fields MAY be present as placeholders for later 9H phases. The system MUST NOT build tenant identity from the user message or from model tool arguments.

#### Scenario: Agent invoke freezes session tenant
- **GIVEN** an authenticated caller with workspace W, user U, and role R
- **WHEN** they call `/ai/agent` or `/ai/agent/stream`
- **THEN** the invoke’s trusted harness context carries W, U, and R
- **AND** those values are not taken from the request body or model output

### Requirement: Agent tools use harness tenant, not model tenant
Search, create, update, and summarize agent tools MUST pass `workspace_id`, `user_id`, and `role` to `NoteService` / `RagService` exclusively from the trusted harness context. Preferred behavior: tool argument schemas omit those tenant fields so the model cannot supply them. Fallback: if schemas must still expose them, the runtime MUST overwrite them from harness context immediately before any service call, MUST ignore model values, and MUST log when a model value differed. Business arguments (query, title, content, note id) remain model-owned.

#### Scenario: Invented workspace does not reach services
- **GIVEN** an agent tool call whose arguments include a `workspace_id` that is not the session workspace (or would have, under the overwrite fallback)
- **WHEN** the tool executes against NoteService or RagService
- **THEN** the service is invoked only with the session workspace from harness context
- **OR** the tool is denied without calling another workspace
- **AND** notes from the foreign workspace are neither read nor written

#### Scenario: Business args stay model-owned
- **GIVEN** a create or update tool call with a model-chosen title or content
- **WHEN** the tool runs under a bound harness context
- **THEN** title/content (and note id for update) still come from the model arguments
- **AND** tenant fields still come only from harness context

### Requirement: Missing harness context fails closed
If trusted harness context is missing at tool execution time, the tool MUST deny the call (forbidden or the closest existing deny string available without inventing the full 9H.2 error envelope). The system MUST NOT default, guess, or parse a workspace id from the user message.

#### Scenario: Tool without context is denied
- **GIVEN** a tool execution path with no harness context available
- **WHEN** search, create, update, or summarize would call a service
- **THEN** the tool returns a denial
- **AND** no NoteService or RagService call is made with a guessed tenant

### Requirement: Chat path remains untouched by tenant bind
Trusted-tenant bind for this change MUST apply to `/ai/agent*` tools only. `/ai/chat` and `/ai/chat/stream` MUST remain the separate fast RAG surface and MUST NOT be replaced by the agent.

#### Scenario: Chat still works without agent tool bind
- **GIVEN** harness tenant bind is enabled for agent tools
- **WHEN** a client calls `/ai/chat` or `/ai/chat/stream`
- **THEN** RAG chat continues to operate on its existing path
- **AND** agent routes remain separately addressable

### Requirement: Invented-workspace behavior is regression-tested without a live model key
The repository MUST include an automated test or fixture golden that asserts a foreign `workspace_id` in tool arguments is not the identity passed into NoteService or RagService. That check MUST run without requiring a live LLM provider key in pull-request CI. A failing assertion MUST fail the test run (not skip).

#### Scenario: CI proves foreign workspace is rejected or overwritten
- **GIVEN** the trusted-tenant bind tests or fixture corpus
- **WHEN** CI runs without a live model API key
- **THEN** the invented-workspace case executes
- **AND** it fails if the foreign workspace id is the one used for the service call
