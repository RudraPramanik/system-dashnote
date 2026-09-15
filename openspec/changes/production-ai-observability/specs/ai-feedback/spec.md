## Purpose

Lets an authenticated workspace user attach a thumbs-up/down or numeric quality rating to their latest AI turn so operators can correlate product feedback with Langfuse traces without a second eval dashboard.

## ADDED Requirements

### Requirement: User can submit feedback on an AI turn
The API MUST accept `POST /ai/feedback` from a valid access JWT. The body MUST identify the turn via `thread_id` (and MAY include an optional client-supplied observation id). The body MUST include a signal of either thumbs (`up` | `down`) or a numeric score in a documented closed range. Workspace identity MUST come from the JWT `wid` only. On success the API MUST attach the score to the corresponding Langfuse observation or trace when Langfuse is enabled.

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
- **AND** chat and agent routes remain usable without ever calling feedback

#### Scenario: Chat does not depend on feedback
- **GIVEN** a client never calls `/ai/feedback`
- **WHEN** they use `/ai/chat` or `/ai/agent` as today
- **THEN** those routes behave as before this change
