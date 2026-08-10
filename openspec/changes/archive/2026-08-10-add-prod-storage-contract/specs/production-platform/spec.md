## MODIFIED Requirements

### Requirement: Production storage uses object store without shared volumes
When `STORAGE_BACKEND` is `r2` (or other S3-compatible remote), the worker MUST download file bytes via `get_storage().download(storage_key)` and MUST NOT depend on a shared filesystem volume with the API. Local development MAY continue using `STORAGE_BACKEND=local` with the Compose `local_storage` volume. Documentation MUST describe the R2 env contract in `.env.production.example` and MUST provide an operator-facing storage contract at `docs/deployment/storage.md` covering why prod needs object storage, the env checklist, and a clear local-dev vs prod comparison. API file upload and worker automation download paths MUST use `get_storage()` (no direct `LOCAL_STORAGE_PATH` filesystem reads for file bytes). When this contract is complete, `docs/documentation/production.md` MUST mark step 7P.4 as done.

#### Scenario: Worker reads upload on R2-backed deploy
- **GIVEN** an uploaded file whose metadata exists in Postgres with a valid `storage_key`
- **AND** `STORAGE_BACKEND` is configured for remote object storage
- **WHEN** the automation worker processes the file upload event
- **THEN** the worker retrieves bytes through `get_storage().download(storage_key)`
- **AND** processing does not require a shared local volume between api and worker

#### Scenario: Local compose storage unchanged
- **GIVEN** local development with `STORAGE_BACKEND=local`
- **WHEN** operators run `docker compose up`
- **THEN** api and worker continue to share the documented local storage volume behavior

#### Scenario: Operator reads storage contract doc
- **GIVEN** Slice 7P.4 is complete
- **WHEN** an operator opens `docs/deployment/storage.md`
- **THEN** the doc explains why prod uses R2/S3-compatible storage (no shared api/worker volume)
- **AND** lists the required env vars (`STORAGE_BACKEND`, `R2_*` or equivalent)
- **AND** contrasts local `STORAGE_BACKEND=local` with prod `STORAGE_BACKEND=r2`

#### Scenario: Tracker updated when storage contract closes
- **GIVEN** storage contract documentation is in place and api/worker use `get_storage()` for file bytes
- **WHEN** the implementer closes Slice 7P.4
- **THEN** `docs/documentation/production.md` shows 7P.4 as complete
