## Purpose

Lets an authenticated workspace user attach a thumbs-up/down or 1–5 quality rating to their AI turn so operators can correlate product feedback with Langfuse traces without putting a judge on the request path.

## ADDED Requirements

### Requirement: User can submit feedback on an AI turn
The API MUST accept `POST /ai/feedback` from a valid access JWT. The body MUST identify the turn via `thread_id` and MUST include a signal of either thumbs (`up` | `down`) or a numeric score from 1 to 5. The body MAY include an optional client-supplied trace id. Workspace identity MUST come from the JWT `wid` only. On success, when Langfuse is enabled, the API MUST attach a user-feedback score to the corresponding Langfuse observation or trace.

#### Scenario: Feedback scores a traced turn
- **GIVEN** the caller has a valid JWT
- **AND** Langfuse is enabled
- **AND** `thread_id` belongs to that JWT workspace
- **WHEN** they POST `/ai/feedback` with thumbs down
- **THEN** the response is success
- **AND** a user-feedback score is visible on the related Langfuse trace

#### Scenario: Foreign thread is rejected
- **GIVEN** thread T belongs to another workspace
- **WHEN** a caller POSTs `/ai/feedback` for T with their JWT
- **THEN** the API MUST NOT attach a score for T
- **AND** the caller receives a not-found or forbidden error (not 200)

### Requirement: Feedback is soft when tracing is disabled
When Langfuse is disabled or scoring fails, `POST /ai/feedback` MUST still authenticate and authorize the thread, then succeed without crashing the API. The response MAY indicate that tracing was unavailable. Existing `/ai/chat*` and `/ai/agent*` contracts MUST NOT require a feedback call to complete a turn.

#### Scenario: Feedback without Langfuse keys
- **GIVEN** Langfuse keys are not set
- **AND** the thread belongs to the caller’s workspace
- **WHEN** they POST `/ai/feedback`
- **THEN** the API does not 5xx
- **AND** the response indicates tracing was unavailable

#### Scenario: Chat does not depend on feedback
- **GIVEN** a client never calls `/ai/feedback`
- **WHEN** they use `/ai/chat` or `/ai/agent` as today
- **THEN** those routes behave as before this change
