## Purpose

Slice 8X CI detail blueprint (`slice8_ci.md`): multi-substep Cursor prompts for thin GitHub Actions CI (8X.1 / 7P.7).

## Requirements

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
The CI blueprint MUST state that local `docker compose` must not be broken, that green CI must not require live LLM/Qdrant/VPS credentials, that CI Python/apt must match the Dockerfile, and that if local pytest is red the inventory/test-job substep MUST stop or document an explicit allowlist rather than silently weakening tests. Optional failure-category guidance (ModuleNotFoundError, missing apt, Settings validation, DB connection) MAY appear in the test-job substep to speed diagnosis without authorizing broad test deletion.

#### Scenario: No live secrets for green CI
- **GIVEN** the CI architecture law / fallbacks
- **WHEN** an implementer configures the PR workflow
- **THEN** they are instructed not to require production host credentials or live LLM keys for a green PR

#### Scenario: Red local pytest stops the train
- **GIVEN** inventory finds largely red local pytest
- **WHEN** the implementer considers forcing CI green
- **THEN** the blueprint requires STOP or an explicit allowlist
- **AND** forbids mass skips to fake green

### Requirement: CI blueprint enforces Dockerfile parity for Python and apt
The CI blueprint MUST instruct implementers that the GitHub Actions Python version and apt packages MUST match the repository `Dockerfile` base image and apt-get layer (inventory-driven). The blueprint MUST NOT hard-require Python 3.11 when the Dockerfile uses a different version. As of this change’s grounding, the Dockerfile uses `python:3.12-slim` and installs `libmagic1`.

#### Scenario: Skeleton uses Dockerfile Python
- **GIVEN** an implementer follows 8X.1.1
- **WHEN** they choose `setup-python` version
- **THEN** the blueprint requires matching the Dockerfile base image tag (currently 3.12)
- **AND** forbids inventing a different major/minor “for CI convenience”

#### Scenario: Apt packages match Dockerfile
- **GIVEN** the CI architecture law / 8X.1.2 guidance
- **WHEN** the test job needs system libraries
- **THEN** the blueprint requires copying packages from the Dockerfile apt layer (including `libmagic1` when present)
- **AND** forbids inventing unrelated system stacks

### Requirement: CI inventory checklist is explicit and service-aware
The CI blueprint’s inventory substep (8X.1.0) MUST require a written report covering at least: `tests/conftest.py` env setdefaults and stubs, `pytest.ini` pythonpath/testpaths, Dockerfile base/apt/requirements path, which requirements file CI should pip-install, local pytest baseline, secrets that MUST NOT appear in CI, and whether any tests need live Postgres/Redis service containers. Service containers MUST be added only when inventory proves need (or documents a conservative include); they MUST NOT be mandated blindly with credentials that diverge from conftest without inventory justification.

#### Scenario: Inventory decides services
- **GIVEN** 8X.1.0 completes
- **WHEN** the report reaches a READY/BLOCKED verdict
- **THEN** it states whether postgres/redis GitHub Actions services are required
- **AND** env examples align with conftest setdefaults when those vars are listed

### Requirement: CI PYTHONPATH hygiene without overstating failure
The CI blueprint MUST note that `pytest.ini` already provides `pythonpath = src` and MUST recommend setting job env `PYTHONPATH: src` as belt-and-suspenders. It MUST NOT claim that every import inevitably fails solely because pytest.ini exists without also setting the env var.

#### Scenario: Job env recommends PYTHONPATH
- **GIVEN** the CI architecture law or 8X.1.1 env section
- **WHEN** an implementer configures the test job
- **THEN** they are instructed to set `PYTHONPATH: src` (or equivalent) in addition to relying on pytest.ini
