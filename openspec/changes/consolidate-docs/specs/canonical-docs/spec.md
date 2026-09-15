## MODIFIED Requirements

### Requirement: Canonical docs use working documentation paths
Canonical docs (`system.md`, `ai.md`, `lld.md`, `observe.md`) MUST link related architecture files under `docs/documentation/` (and other surviving `docs/` paths). Observability MUST have a single operator path: `docs/documentation/observe.md`. They MUST NOT send readers to `src/docs/` as if those files still exist, and MUST NOT list `docs/observability.md` as a current second observability guide.

#### Scenario: Cross-links resolve in-repo
- **WHEN** a reader follows related-doc links from `system.md` or `ai.md`
- **THEN** each link targets an existing path under `docs/`
- **AND** no canonical related-doc table lists `src/docs/system.md` or `src/docs/ai.md` as current locations

#### Scenario: Observability has one current guide
- **WHEN** a reader looks up logging, Langfuse, or Prometheus from canonical docs
- **THEN** they are sent to `docs/documentation/observe.md`
- **AND** they are not sent to `docs/observability.md` as a live sibling runbook

## ADDED Requirements

### Requirement: Related-doc maps list only surviving files
The root README Documentation section and canonical related-doc tables MUST list only files that exist after docs consolidation. They MUST NOT point at deleted historical slice prompts, `docs/ship-plan.md`, `docs/nvidia.md`, `docs/documentation/issue_solve.md`, `docs/uml/README.md`, or root `n.md`.

#### Scenario: README documentation links resolve
- **GIVEN** consolidation is complete
- **WHEN** a reader follows every link in the README Documentation section
- **THEN** each target file exists in the repository
- **AND** the section does not advertise deleted blueprint slice files as current
