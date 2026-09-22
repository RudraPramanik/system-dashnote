## MODIFIED Requirements

### Requirement: Architecture discoverability
README MUST link to existing system/AI documentation (at least `docs/documentation/system.md`, `docs/documentation/ai.md`, and UML or LLD docs) so reviewers can navigate tenancy and AI laws without hunting the tree. The Documentation index MUST also surface `docs/documentation/auth.md`, `docs/documentation/observe.md`, and `docs/documentation/lld.md` (or UML as the diagram entry) when those files exist. README MUST briefly acknowledge inbound integrations (`/integrations` or a link to `docs/inbound-channels.md`) so strangers do not assume the product is notes-only HTTP.

#### Scenario: Architecture links resolve
- **GIVEN** the updated root README
- **WHEN** a reader follows the architecture documentation links
- **THEN** they reach in-repo docs that describe routing/tenancy and AI behavior

#### Scenario: Keep-set docs are findable from README
- **WHEN** a stranger opens the README Documentation section
- **THEN** they find links to auth, observability, and LLD (or UML) keep-set docs
- **AND** they find a pointer to inbound integrations without a production-live claim

#### Scenario: Integrations are not invisible
- **WHEN** a reader skims README capabilities or architecture
- **THEN** inbound email/WhatsApp (or `/integrations`) is mentioned or linked
- **AND** HTTPS production-live remains pending until smoke evidence exists
