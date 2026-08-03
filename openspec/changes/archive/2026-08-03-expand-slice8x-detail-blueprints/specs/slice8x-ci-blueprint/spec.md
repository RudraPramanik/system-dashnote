## ADDED Requirements

### Requirement: Slice 8X CI detail blueprint exists
The repository MUST include `docs/documentation/blueprint/slice8_ci.md` as the executable multi-substep blueprint for thin GitHub Actions CI (Slice 8X.1 / 7P.7). The document MUST be Cursor-ready (paste-first architecture law + per-substep objective prompts), not a single undifferentiated task list.

#### Scenario: Operator opens CI blueprint
- **GIVEN** this change is complete
- **WHEN** an operator opens `slice8_ci.md`
- **THEN** the file is non-empty
- **AND** it identifies itself as the detail blueprint for 8X.1 / thin CI
- **AND** it links back to `slice8_X.md`

### Requirement: CI blueprint defines ordered substages with gates
The CI blueprint MUST define ordered substages covering at least: inventory of local test/CI prerequisites, workflow skeleton without production secrets, pytest job green in CI, and docker build job plus overall CI gate. Later substages MUST NOT be required to start earlier ones.

#### Scenario: CI phase order
- **GIVEN** the CI blueprint overview
- **WHEN** an implementer reads the substage list
- **THEN** inventory appears before workflow authoring
- **AND** the test job is gated before treating docker build as the final CI success
- **AND** production VPS secrets and SSH deploy are forbidden in this workflow

### Requirement: CI blueprint states fallbacks and never-break rules
The CI blueprint MUST state that local `docker compose` must not be broken, that green CI must not require live LLM/Qdrant/VPS credentials, and that if local pytest is red the inventory/fix-job substep MUST stop or document an explicit allowlist rather than silently weakening tests.

#### Scenario: No live secrets for green CI
- **GIVEN** the CI architecture law / fallbacks
- **WHEN** an implementer configures the PR workflow
- **THEN** they are instructed not to require production host credentials or live LLM keys for a green PR
