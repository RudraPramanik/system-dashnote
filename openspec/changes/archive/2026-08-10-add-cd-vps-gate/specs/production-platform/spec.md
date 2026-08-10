## MODIFIED Requirements

### Requirement: CD deploys main and runs smoke
A CD workflow MUST exist at `.github/workflows/deploy.yml` and MUST deploy to the configured VPS (or documented target) only on `workflow_dispatch` and on pushes of version tags matching `v*` — it MUST NOT auto-deploy on every push or merge to the default branch. The workflow MUST build and push the application image to GHCR (or the documented registry), set the VPS `IMAGE` (or equivalent compose image override already used by `docker-compose.prod.yml`) to that tag, run migrations as needed, update api/worker (and documented edge services), and execute hard health verification plus `scripts/smoke_prod.py`. Deploy MUST be considered failed if health-check or smoke exits non-zero. `docs/deployment/runbook.md` MUST document required GitHub Secrets, trigger rules, and a production gate checklist. When this deliverable is complete, `docs/documentation/production.md` MUST mark step 7P.8 as done.

#### Scenario: Tag or manual dispatch triggers deploy and smoke
- **GIVEN** CD secrets and a configured VPS environment
- **WHEN** an operator pushes a `v*` tag or runs `workflow_dispatch`
- **THEN** the deploy workflow builds and pushes an image to the documented registry
- **AND** updates running services on the VPS (migrate then up, using existing deploy helpers or equivalent)
- **AND** runs hard health verification
- **AND** runs `scripts/smoke_prod.py` against the configured production base URL
- **AND** fails the workflow if health-check or smoke exits non-zero

#### Scenario: Merge to default branch does not auto-deploy
- **GIVEN** CD is configured
- **WHEN** a change is merged or pushed to the default branch without a `v*` tag and without `workflow_dispatch`
- **THEN** the deploy workflow does not run solely because of that merge/push

#### Scenario: Scripts and secrets stay out of the workflow files
- **GIVEN** the contents of `.github/workflows/deploy.yml`
- **WHEN** an operator reviews the workflow before enabling secrets
- **THEN** no production passwords, API keys, or connection strings are hard-coded
- **AND** VPS host credentials and smoke base URL come from GitHub Secrets (or documented vars)

#### Scenario: Runbook documents CD secrets and production gate
- **GIVEN** Slice 7P.8 is complete
- **WHEN** an operator opens `docs/deployment/runbook.md`
- **THEN** a GitHub Secrets / CD section lists required secrets and trigger rules (`v*` / `workflow_dispatch`)
- **AND** a production gate checklist includes hard health and smoke success before claiming production-live

#### Scenario: Tracker updated when CD gate closes
- **GIVEN** `deploy.yml`, compose image override compatibility, and runbook CD/gate docs are in place
- **WHEN** the implementer closes Slice 7P.8
- **THEN** `docs/documentation/production.md` shows 7P.8 as complete

## ADDED Requirements

### Requirement: Prod compose accepts registry image without rebuild
`docker-compose.prod.yml` MUST allow api, worker, and migrate to run from a registry image via the existing `IMAGE` environment variable (defaulting to a local tag when unset) so a CD deploy can `docker pull` and start services without requiring an on-VPS source rebuild. Local developer compose (`docker-compose.yml`) MUST remain the default path and MUST NOT be required to change for this behavior.

#### Scenario: VPS pulls CD image via IMAGE
- **GIVEN** `IMAGE` is set to a GHCR (or documented registry) tag on the VPS
- **WHEN** an operator runs prod compose up (directly or via deploy helpers)
- **THEN** api/worker/migrate use that image
- **AND** a full on-server `docker build` is not required for that release

#### Scenario: Unset IMAGE still allows local prod compose build
- **GIVEN** `IMAGE` is unset
- **WHEN** an operator runs `docker compose -f docker-compose.prod.yml` with build available
- **THEN** services can still build from the local Dockerfile as today
