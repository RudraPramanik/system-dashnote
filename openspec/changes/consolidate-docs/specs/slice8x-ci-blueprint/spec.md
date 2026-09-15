## ADDED Requirements

### Requirement: Thin CI operator truth is the shipped workflow
Operators MUST find thin CI guidance from surviving docs (`docs/documentation/production.md` and/or blueprint8 links) plus the GitHub Actions workflow in the repo. The repository MUST NOT require `docs/documentation/blueprint/slice8_ci.md` to exist.

#### Scenario: Operator does not need slice8_ci.md
- **GIVEN** this change is complete
- **WHEN** an operator looks up PR CI behavior
- **THEN** they can identify the workflow and production/CI notes without opening `slice8_ci.md`

## REMOVED Requirements

### Requirement: Slice 8X CI detail blueprint exists
**Reason**: Thin CI already shipped; the Composer prompt file is leftover.
**Migration**: Inspect `.github/workflows/` and `docs/documentation/production.md`.

### Requirement: CI blueprint defines ordered substages with gates
**Reason**: Implementation substages are complete; remaining CI truth is the workflow.
**Migration**: Treat the live workflow as the contract; change it via a CI-focused OpenSpec change if needed.

### Requirement: CI blueprint states fallbacks and never-break rules
**Reason**: Never-break local compose and no-prod-secrets rules live in `deploy-low.md` / production docs and `thin-ci` spec.
**Migration**: Follow those surviving docs and specs.

### Requirement: CI blueprint enforces Dockerfile parity for Python and apt
**Reason**: Parity is a CI implementation concern owned by the workflow and Dockerfile, not a retired prompt file.
**Migration**: Keep workflow/Dockerfile aligned; do not restore `slice8_ci.md`.

### Requirement: CI inventory checklist is explicit and service-aware
**Reason**: Inventory-first Composer substages are complete.
**Migration**: No operator file required; CI inventory is historical.

### Requirement: CI PYTHONPATH hygiene without overstating failure
**Reason**: pytest.ini / CI env already encode this.
**Migration**: Keep pytest.ini as source of truth.
