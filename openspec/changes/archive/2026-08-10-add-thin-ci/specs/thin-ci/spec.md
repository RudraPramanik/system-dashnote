## ADDED Requirements

### Requirement: CI readiness inventory precedes workflow authoring
The implementer MUST produce a written CI readiness inventory before creating `.github/workflows/ci.yml` (unless the operator explicitly expands scope). The inventory MUST cover at least: `tests/conftest.py` env setdefaults and stubs, `pytest.ini` pythonpath/testpaths settings, Dockerfile base image and apt packages and requirements install path, which requirements file CI SHALL pip-install, whether GitHub Actions postgres/redis service containers are needed, a local or cited `pytest` baseline, and secrets that MUST NOT be required for green CI. The inventory MUST end with a READY or BLOCKED verdict.

#### Scenario: Inventory blocks YAML when pytest is largely red
- **GIVEN** local or cited `python -m pytest -q` is largely failing
- **WHEN** the inventory is completed
- **THEN** the verdict is BLOCKED (or READY only with an explicit documented allowlist)
- **AND** the implementer MUST NOT proceed to claim CI success by mass-skipping tests

#### Scenario: Inventory decides service containers
- **GIVEN** the inventory examines how tests obtain DB/Redis
- **WHEN** the report is finished
- **THEN** it states READY-without-services, NEED postgres, NEED redis, or NEED both
- **AND** it cites evidence rather than defaulting to both services

### Requirement: Thin PR CI runs pytest then Docker build without production secrets
The repository MUST provide a GitHub Actions workflow (preferred path `.github/workflows/ci.yml`) that runs on pull requests and on pushes to the default branch. The workflow MUST execute a pytest job and a Docker image build job that depends on the test job succeeding. The workflow MUST NOT require production VPS credentials, SSH deploy keys, or live LLM/Qdrant API keys for a green result. Job env for tests MUST align with inventory/conftest safe placeholders and MUST include `PYTHONPATH: src` as belt-and-suspenders alongside `pytest.ini`.

#### Scenario: PR CI green without prod secrets
- **GIVEN** a pull request whose tests pass under fixture/stub-friendly env
- **WHEN** the thin CI workflow executes
- **THEN** pytest completes successfully without production host or live AI provider secrets
- **AND** the Docker build job runs only after the test job succeeds
- **AND** the build does not require BuildKit secrets for LLM keys

#### Scenario: No deploy in thin CI
- **GIVEN** the thin CI workflow file
- **WHEN** an operator inspects jobs and steps
- **THEN** there is no SSH deploy, no production registry login requiring prod credentials, and no CD job

### Requirement: CI Python and apt match the Dockerfile
The CI test job MUST use a Python version matching the repository Dockerfile base image tag and MUST install the same apt packages as the Dockerfile apt-get layer when those packages are needed for tests (inventory-driven). As of current grounding, that means Python 3.12 for `python:3.12-slim` and `libmagic1` when present in the Dockerfile. CI MUST NOT invent a different Python minor “for convenience.”

#### Scenario: setup-python matches Dockerfile
- **GIVEN** the Dockerfile `FROM` line uses `python:3.12-slim`
- **WHEN** the CI workflow configures `setup-python`
- **THEN** the configured version is 3.12 (or the Dockerfile’s then-current major.minor)
- **AND** the workflow does not hard-require 3.11 solely because a review doc said so

#### Scenario: Apt parity for libmagic
- **GIVEN** the Dockerfile installs `libmagic1`
- **WHEN** the CI test job needs system libraries for imports or native deps
- **THEN** the job installs `libmagic1` (and any other packages from that Dockerfile apt layer)
- **AND** does not invent an unrelated apt stack

### Requirement: Local docker compose remains unbroken
Implementing thin CI MUST NOT edit `docker-compose.yml` in ways that break local `docker compose up` for the full stack (db, redis, qdrant, api, worker, nginx). Application source and conftest MUST NOT be rewritten for CI convenience unless a minimal fix is required for honest green tests and documented in the change.

#### Scenario: Local compose path intact after CI lands
- **GIVEN** thin CI has been added
- **WHEN** an operator runs the existing local compose workflow
- **THEN** the full local stack definition remains usable as before
- **AND** CI-only concerns live in the GitHub Actions workflow (and optional short docs), not in a broken compose file

### Requirement: Platform tracker marks 7P.7 when thin CI is complete
When pytest and Docker build succeed on CI without production secrets, `docs/documentation/production.md` MUST mark step 7P.7 (CI) as done.

#### Scenario: Tracker updated at gate close
- **GIVEN** the thin CI gate is green (pytest + docker build, no prod secrets)
- **WHEN** the implementer closes Slice 8X.1 / 7P.7
- **THEN** `production.md` shows 7P.7 as complete
