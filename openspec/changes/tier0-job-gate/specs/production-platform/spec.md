## ADDED Requirements

### Requirement: Production-live claim requires HTTPS smoke evidence
Operators MUST NOT claim production-live or mark A-gate complete until both (1) `GET https://<prod-api>/health` returns success for hard dependencies and (2) `scripts/smoke_prod.py` exits 0 against that HTTPS base URL. Existence of CD workflow files alone MUST NOT satisfy this claim. When evidence is captured, `docs/documentation/blueprint/goal.md` A-gate items that correspond to live smoke/TLS MUST be updated to reflect the recorded result.

#### Scenario: Workflow files without smoke do not close A-gate
- **GIVEN** `.github/workflows/deploy.yml` and deploy helpers exist
- **AND** no successful `smoke_prod.py` run against the production HTTPS URL has been recorded
- **WHEN** an operator reviews whether production-live may be claimed
- **THEN** the claim MUST remain false
- **AND** A-gate live smoke/TLS boxes MUST remain incomplete

#### Scenario: HTTPS health and smoke close the live claim
- **GIVEN** `GET https://<prod-api>/health` succeeds for hard dependencies
- **AND** `SMOKE_BASE_URL=https://<prod-api>` `python scripts/smoke_prod.py` exits 0
- **WHEN** the operator records that evidence and updates the job-search tracker
- **THEN** production-live MAY be claimed for A-gate
- **AND** corresponding A4/A7-style items in `goal.md` MUST be marked complete
