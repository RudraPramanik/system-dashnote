## ADDED Requirements

### Requirement: API CORS allows the stranger-demo frontend origin
For B-gate against a browser-hosted sibling frontend, the API MUST include the frontend origin in `CORS_ORIGINS` (local and production as applicable). Clients MUST continue to send `Authorization: Bearer` and MUST NOT override tenancy via client-chosen workspace ids. Misconfigured CORS that blocks the demo path MUST be treated as B-gate incomplete.

#### Scenario: Browser FE can call the API
- **GIVEN** the sibling frontend origin is listed in API `CORS_ORIGINS`
- **WHEN** a browser client performs register/login and authenticated notes/AI calls
- **THEN** those requests MUST NOT fail solely due to CORS rejection
- **AND** workspace scope remains JWT-derived

#### Scenario: Missing FE origin blocks B-gate
- **GIVEN** the frontend origin is absent from production `CORS_ORIGINS`
- **WHEN** a stranger attempts the demo from the browser app
- **THEN** B-gate MUST remain incomplete until CORS (or equivalent access) is fixed

### Requirement: B-gate completion is tracked as proven demo path
Closing B-gate REQUIRES the stranger demo path (register → note → file upload → RAG with citation from SSE `metadata` → agent mutation) to be runnable against the target API, with B1–B7 progress reflected in `docs/documentation/blueprint/goal.md`. The frontend guide checklist alone MUST NOT count as B-gate complete without demo evidence. Frontend UI implementation MAY live in the sibling `dashnotes` repository; this capability still requires API-side readiness and tracker honesty in this repository.

#### Scenario: Guide checklist without demo does not close B
- **GIVEN** `frontendguide.md` lists B1–B7
- **AND** the stranger demo has not been proven against the target API
- **WHEN** an operator reviews job-search readiness
- **THEN** B-gate MUST remain incomplete in `goal.md`

#### Scenario: Proven demo closes B-gate tracker
- **GIVEN** the stranger demo path works end-to-end against the target API (including citations from `metadata` and agent tool visibility)
- **WHEN** the operator updates the job-search tracker
- **THEN** corresponding B items in `goal.md` MUST be marked complete
- **AND** chat and agent surfaces MUST both remain available in the demo
