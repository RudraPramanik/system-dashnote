## ADDED Requirements

### Requirement: System and AI docs describe conversation auto-titles
`docs/documentation/system.md` and `docs/documentation/ai.md` MUST document that chat and agent threads receive a one-shot auto-title after the first successful turn (deterministic truncate with optional LLM polish; no historical backfill). They MUST document `PATCH /ai/threads/{thread_id}` for manual rename and MUST note that streaming clients may receive a `title` field on relevant SSE events. They MUST link or point to `docs/documentation/smoke-conversation-titles.md` for verification.

#### Scenario: Reader finds auto-title and thread rename
- **GIVEN** the API auto-titles threads on first turn and exposes `PATCH /ai/threads/{thread_id}`
- **WHEN** a reader opens `system.md` or `ai.md`
- **THEN** one-shot auto-title behavior and the rename route are described
- **AND** the docs MUST NOT imply titles are backfilled for all historical threads

#### Scenario: SSE title is discoverable from AI contract docs
- **WHEN** a reader looks up chat or agent streaming contracts in `ai.md`
- **THEN** they find that a `title` field MAY appear on the documented SSE metadata / done (or equivalent) events after auto-title

### Requirement: System doc points to production and devops runbooks
`docs/documentation/system.md` MUST keep local Compose accurate and MUST cross-link production/ops docs (`docs/devops-progress.md`, `docs/deployment/runbook.md`, `docs/documentation/production.md`) so readers can find the VPS first-boot path, IMAGE pull strategy, and HTTP-first-boot vs HTTPS distinction without treating first-boot HTTP as the final production-live claim.

#### Scenario: Reader finds ops path from system.md
- **WHEN** a reader follows production or devops links from the Docker / deploy section of `system.md`
- **THEN** each link targets an existing path under `docs/`
- **AND** the system doc MUST NOT claim Grafana is a default local Compose service

#### Scenario: Devops progress status matches recorded evidence
- **GIVEN** `docs/documentation/blueprint/goal.md` records HTTP-IP first-boot evidence as PASS
- **WHEN** a reader checks `docs/devops-progress.md` current level / Phase 1 status
- **THEN** it MUST NOT contradict that PASS for HTTP-IP first-boot
- **AND** HTTPS / later phases MAY remain open
