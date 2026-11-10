## MODIFIED Requirements

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
