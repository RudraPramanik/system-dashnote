## Purpose

Names stricter AI request ceilings and trusted Redis key shapes, and refuses a chat or agent completion when the user-minute or workspace-day counter is over.

## Requirements

### Requirement: AI budget settings are configurable and stricter than the global limit
The system MUST expose three settings: `AI_USER_REQUESTS_PER_MINUTE`, `AI_WORKSPACE_REQUESTS_PER_DAY`, and `AI_TOKEN_BUDGET_PER_DAY`. Each MUST load from the environment. The default for `AI_USER_REQUESTS_PER_MINUTE` MUST be an integer strictly below 100. The default for `AI_WORKSPACE_REQUESTS_PER_DAY` MUST be a positive integer. The default for `AI_TOKEN_BUDGET_PER_DAY` MUST be an integer greater than or equal to zero, and zero MUST mean the token ceiling is not configured. These defaults MUST be documented as defaults. They MUST NOT be described as a frozen production quota. Existing settings MUST keep their current defaults. `/ai/chat*` and `/ai/agent*` MUST both remain.

#### Scenario: Defaults load below the global ceiling
- **GIVEN** no environment override for the three AI budget settings
- **WHEN** settings load
- **THEN** `AI_USER_REQUESTS_PER_MINUTE` is an integer strictly below 100
- **AND** `AI_WORKSPACE_REQUESTS_PER_DAY` is a positive integer
- **AND** `AI_TOKEN_BUDGET_PER_DAY` is zero or a positive integer
- **AND** an example environment file names all three variables

#### Scenario: An operator can override each ceiling
- **GIVEN** environment values for the three AI budget settings
- **WHEN** settings load
- **THEN** each setting equals its environment value
- **AND** the global API limiter remains a separate 100-requests-per-minute control

### Requirement: Budget keys use trusted user and workspace identity
Key text MUST use only a server-bound user id and a server-bound workspace id. The user-minute key MUST be `ai_req:{user_id}:{minute_bucket}`. The workspace-day key MUST be `ai_day:{workspace_id}:{day_bucket}`. The token key MUST be `ai_tok:{workspace_id}:{day_bucket}`. `minute_bucket` MUST be the UTC epoch minute. `day_bucket` MUST be the UTC calendar date `YYYYMMDD`. The same workspace and the same UTC day MUST produce the same day bucket on the day key and the token key. Role MUST NOT appear in any budget key. A model-supplied user id or workspace id MUST NOT be a separate input that can override the trusted ids. A missing or blank user id MUST NOT produce a user-minute key, including any shared anonymous key. A missing or blank workspace id MUST NOT produce a workspace-day key or a token key.

#### Scenario: Distinct trusted identities get distinct keys
- **GIVEN** trusted user U1 in workspace W1 and trusted user U2 in workspace W2
- **AND** a fixed UTC timestamp
- **WHEN** budget keys are built for each pair
- **THEN** the user-minute keys differ
- **AND** the workspace-day keys differ
- **AND** each user-minute key starts with `ai_req:` and contains that user's id and the UTC epoch minute
- **AND** each workspace-day key starts with `ai_day:` and contains that workspace id and the UTC date `YYYYMMDD`
- **AND** the token key for a workspace uses `ai_tok:` with that same workspace id and the same UTC date
- **AND** none of the keys contain a role

#### Scenario: A missing identity does not share a bucket
- **GIVEN** a blank user id or a blank workspace id
- **WHEN** a budget key is requested for that missing side
- **THEN** no key is produced for that side
- **AND** the result is not a shared key such as one containing `anonymous` or an empty identity segment

#### Scenario: The UTC day does not follow the server's local timezone
- **GIVEN** a timestamp that is still the previous UTC date in a timezone behind UTC
- **WHEN** the day bucket is built
- **THEN** the day bucket is the UTC date
- **AND** the minute bucket is the UTC epoch minute for that timestamp

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
If the Redis client is missing, or the budget check raises a Redis connection or timeout error, the system MUST log a warning and MUST allow that completion. An over-limit counter MUST still deny. `/health` and `/health/ai` MUST NOT read or write AI budget keys. Every budget decision MUST increment one outcome counter by one. The only distinguishing label MUST be the outcome: `allowed`, `denied`, or `fail_open`. The counter MUST NOT carry a user id, a workspace id, or a role. A missing identity that denies the call MUST count as `denied` and MUST NOT write a shared anonymous key. `/ai/chat*` and `/ai/agent*` MUST both remain.

#### Scenario: A Redis error does not become a server error
- **GIVEN** the budget check's Redis call fails with a connection error
- **WHEN** a client calls `/ai/chat` or `/ai/agent`
- **THEN** the request is not refused for budget
- **AND** the response is not HTTP 500 caused by that Redis error
- **AND** a warning is logged
- **AND** the outcome counter increases by one for `fail_open`

#### Scenario: An over-limit counter is denied and counted
- **GIVEN** a user-minute or workspace-day ceiling already reached for a trusted identity
- **WHEN** that identity requests another chat or agent completion
- **THEN** the provider is not called
- **AND** the outcome counter increases by one for `denied`
- **AND** the counter series is the same one used for an allowed call

#### Scenario: Health does not touch AI budget keys
- **GIVEN** the AI budget check exists
- **WHEN** a client calls `/health` or `/health/ai`
- **THEN** those handlers do not increment or read `ai_req`, `ai_day`, or `ai_tok` keys
- **AND** the budget outcome counter does not change

#### Scenario: Distinct tenants share one outcome series
- **GIVEN** trusted user U1 in workspace W1 and trusted user U2 in workspace W2
- **WHEN** each is allowed one completion
- **THEN** both decisions increment the same outcome series for `allowed`
- **AND** neither series name nor label contains a user id, a workspace id, or a role
