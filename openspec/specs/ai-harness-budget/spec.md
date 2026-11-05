## Purpose

Names stricter AI request ceilings and the trusted Redis key shapes a later substep will enforce, without refusing any call in this change.

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

### Requirement: This change names ceilings and does not enforce them
Loading the settings and building key text MUST NOT contact Redis, MUST NOT increment a counter, and MUST NOT refuse `/ai/chat`, `/ai/chat/stream`, `/ai/agent`, `/ai/agent/stream`, or `/ai/agent/resume`. `budget_exceeded` MUST stay a reserved tool-error code and MUST NOT be returned because a counter tripped. `HarnessContext.remaining_budget` MUST stay unused and MUST NOT be treated as the budget store. `/health` and `/health/ai` MUST stay independent of AI budget keys. A Redis outage MUST NOT change AI behavior in this change, because this change does not read Redis. Workspace isolation and note role checks from earlier harness phases MUST stay in force. No note or vector write is added.

#### Scenario: Chat and agent still proceed
- **GIVEN** the AI budget settings exist
- **WHEN** a client calls `/ai/chat` or `/ai/agent` under the current product path
- **THEN** the call is not refused for an AI budget
- **AND** no HTTP 429 and no SSE `budget_exceeded` event are introduced by these settings
- **AND** both routes remain separately addressable

#### Scenario: Key text does not require Redis
- **GIVEN** trusted user and workspace ids and a UTC timestamp
- **WHEN** the three key strings are built
- **THEN** the strings match the required shapes
- **AND** Redis is not read or written
- **AND** `remaining_budget` on the harness context stays unset
