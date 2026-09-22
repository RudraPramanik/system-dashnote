## ADDED Requirements

### Requirement: SSE heartbeat awareness for quiet streams
The frontend guide MUST document that AI SSE streams MAY emit comment/heartbeat frames to keep proxies (including Nginx) from closing quiet connections. Clients MUST ignore comment frames for answer rendering and MUST continue to require visible failure when a stream closes with no token, done, approval_required, or error content. The guide MUST NOT require UI chrome for heartbeats and MUST NOT treat heartbeats as a B-gate checklist item.

#### Scenario: Guide mentions heartbeats without requiring UI
- **WHEN** a frontend debugs a quiet chat or agent stream through Nginx
- **THEN** `docs/documentation/frontendguide.md` states that heartbeat/comment frames may appear
- **AND** states that clients ignore them for rendering
- **AND** does not add heartbeat UI to the B-gate checklist
