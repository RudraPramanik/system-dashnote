## ADDED Requirements

### Requirement: Optional AI feedback client contract
The frontend guide MUST document `POST /ai/feedback` as an optional client call after a chat or agent turn. The body MUST use `thread_id` plus either thumbs (`up` / `down`) or a numeric score (1–5), and MAY include `trace_id` when the API returned one. Workspace identity MUST come from the JWT only — the client MUST NOT send `workspace_id` to override tenancy. The guide MUST NOT require a feedback UI for B-gate. Chat and agent turns MUST remain usable without calling feedback.

#### Scenario: Guide documents the feedback endpoint
- **WHEN** a frontend looks up post-turn AI APIs in `docs/documentation/frontendguide.md`
- **THEN** the guide lists `POST /ai/feedback` with `thread_id` and thumbs or score
- **AND** states that `workspace_id` MUST NOT be sent to override JWT `wid`

#### Scenario: B-gate does not require thumbs UI
- **WHEN** a reader follows the B-gate checklist
- **THEN** feedback UI is optional
- **AND** register → note → file → RAG citation → agent mutation remains the required demo path
