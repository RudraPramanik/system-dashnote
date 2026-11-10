## REMOVED Requirements

### Requirement: This change names ceilings and does not enforce them
**Reason**: 9H.4.2 enforces the user-minute and workspace-day counters before a model completion. The requirement forbade that refusal.
**Migration**: Request ceilings are checked by the added requirements below. `budget_keys` still only formats key text. `remaining_budget` stays unused. The token key is still not incremented.

## ADDED Requirements

### Requirement: Request ceilings are consumed before each model completion
Before a chat or agent provider completion, the system MUST increment the trusted user-minute key and the trusted workspace-day key built for the JWT user id and workspace id. The check MUST run once per completion: on `/ai/chat` and `/ai/chat/stream` before retrieval answers, and inside the agent model node before each completion, including `/ai/agent/resume` and a later iteration after tools. The same completion MUST NOT be counted twice. `/ai/agent/reject`, thread routes, and feedback MUST NOT increment these keys. The token key MUST NOT be incremented. `budget_keys` MUST remain a pure formatter and MUST NOT open Redis. `remaining_budget` on the harness context MUST stay unused. Role checks and workspace isolation from earlier harness phases MUST stay in force. `/ai/chat*` and `/ai/agent*` MUST both remain. No note or vector write is added.

#### Scenario: One completion increments each request key once
- **GIVEN** trusted user U in workspace W and ceilings above zero
- **WHEN** one chat answer or one agent model completion is allowed
- **THEN** the user-minute key and the workspace-day key for that UTC bucket each increase by one
- **AND** the token key is not written
- **AND** `remaining_budget` stays unset

#### Scenario: Reject, threads, and feedback do not spend a request
- **GIVEN** an authenticated caller
- **WHEN** they reject an agent action or use thread or feedback routes
- **THEN** the AI request counters are unchanged

### Requirement: Over budget is a controlled refusal and does not call the provider
When the user-minute count or the workspace-day count is above its configured ceiling, the system MUST NOT call the LLM provider for that completion and MUST NOT emit further tokens from it. `POST /ai/chat` and `POST /ai/agent` MUST return HTTP 429. `POST /ai/chat/stream` and `POST /ai/agent/stream` MUST emit one SSE object with `type` `error` and `code` `budget_exceeded`, including retry guidance, then end the stream. When the window end is known, the 429 MUST include `Retry-After`. When it is not known, the header MAY be omitted and the message MUST still tell the client to retry shortly. The status MUST NOT be 500. A denial between agent tool iterations MUST use that same client refusal and MUST NOT start another provider completion. Note tools MUST NOT return `budget_exceeded` themselves. A blank user id or a blank workspace id MUST deny the call and MUST NOT write a shared anonymous key.

#### Scenario: A tiny limit refuses chat before the model
- **GIVEN** a user-minute or workspace-day ceiling of one and a counter already at that ceiling
- **WHEN** the client calls `POST /ai/chat`
- **THEN** the response is HTTP 429
- **AND** the model client is not called

#### Scenario: A stream ends with budget_exceeded
- **GIVEN** the same exhausted ceiling
- **WHEN** the client calls `POST /ai/chat/stream` or `POST /ai/agent/stream`
- **THEN** the stream emits an error object whose code is `budget_exceeded`
- **AND** the stream then ends
- **AND** the model client is not called for that completion

#### Scenario: A missing identity does not share a bucket
- **GIVEN** a blank user id or a blank workspace id on an AI generation route
- **WHEN** the budget check runs
- **THEN** the call is denied
- **AND** no key containing `anonymous` or an empty identity segment is written

### Requirement: Redis trouble allows the AI call
If the Redis client is missing, or the budget check raises a Redis connection or timeout error, the system MUST log a warning and MUST allow that completion. An over-limit counter MUST still deny. `/health` and `/health/ai` MUST NOT read or write AI budget keys. This change MUST NOT add a Prometheus series for budget outcomes.

#### Scenario: A Redis error does not become a server error
- **GIVEN** the budget check's Redis call fails with a connection error
- **WHEN** a client calls `/ai/chat` or `/ai/agent`
- **THEN** the request is not refused for budget
- **AND** the response is not HTTP 500 caused by that Redis error
- **AND** a warning is logged

#### Scenario: Health does not touch AI budget keys
- **GIVEN** the AI budget check exists
- **WHEN** a client calls `/health` or `/health/ai`
- **THEN** those handlers do not increment or read `ai_req`, `ai_day`, or `ai_tok` keys
