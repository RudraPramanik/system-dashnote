## ADDED Requirements

### Requirement: Root README presents a stranger-test pitch
The root `readme.md` MUST include: a one-sentence product pitch, stack summary, pointer to architecture documentation, and a “built” capability summary covering RAG, agent, workers/automation, and local Compose. When live URLs exist, they MUST be linked; until then placeholders or “pending deploy” MUST be explicit.

#### Scenario: New reader understands the product from README
- **GIVEN** a reader opens the root README with no prior context
- **WHEN** they read the pitch, stack, built table, and doc links
- **THEN** they can identify what DashNoteSystem is and which major AI surfaces exist
- **AND** they are directed to canonical architecture docs for depth

### Requirement: Metrics and demo evidence are honest
README (or clearly linked docs) MUST provide placeholders or filled values for eval pass rate and cost/latency notes. The project MUST NOT claim “production-ready” or “live demo” unless corresponding smoke/CI or live URL evidence exists. Demo video links MAY be external (Loom/YouTube) referenced from README.

#### Scenario: No false production claims
- **GIVEN** production smoke or live TLS URL is not yet verified
- **WHEN** a reader reviews README claims
- **THEN** the README does not assert an unverified live production deployment as complete
- **AND** any metrics section distinguishes documented measurements from TODOs

#### Scenario: Metrics section present
- **GIVEN** the portfolio baseline docs are updated
- **WHEN** a reader looks for quality/cost signals
- **THEN** they find an eval pass-rate field and a cost/latency field (filled or explicitly pending)

### Requirement: Architecture discoverability
README MUST link to existing system/AI documentation (e.g. `docs/documentation/system.md`, `docs/documentation/ai.md`, and/or UML docs) so reviewers can navigate tenancy and AI laws without hunting the tree.

#### Scenario: Architecture links resolve
- **GIVEN** the updated root README
- **WHEN** a reader follows the architecture documentation links
- **THEN** they reach in-repo docs that describe routing/tenancy and AI behavior
