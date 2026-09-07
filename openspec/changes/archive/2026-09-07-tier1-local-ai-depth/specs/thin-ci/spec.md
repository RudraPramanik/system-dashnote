## ADDED Requirements

### Requirement: PR CI runs fixture evals without live LLM keys
The thin PR CI workflow MUST include a job or step that executes the golden eval harness in fixture mode (e.g. `python evals/run_eval.py --mode fixture` with `PYTHONPATH=src` as needed). That step MUST NOT require live LLM provider keys, production VPS credentials, or SSH. Failure of fixture evals MUST fail the CI check.

#### Scenario: Fixture evals gate the PR
- **GIVEN** a pull request that breaks a fixture golden assertion
- **WHEN** thin CI runs
- **THEN** the fixture-eval step exits non-zero
- **AND** the workflow does not call live LLM APIs to evaluate those fixtures

#### Scenario: Green CI still needs no prod secrets
- **GIVEN** fixture goldens and unit tests pass
- **WHEN** thin CI completes
- **THEN** green status still does not depend on production host secrets or live AI keys
