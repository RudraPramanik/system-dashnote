## ADDED Requirements

### Requirement: Eval runner supports fixture and live modes
The eval runner MUST support both a deterministic `fixture` mode (recorded/stubbed responses; no live LLM keys required) and a `live` mode that calls a configurable API `--base-url` with auth token(s). C-gate operator proof MAY use `live` against local or production. PR CI MUST NOT require `live` mode or paid live LLM keys to stay green.

#### Scenario: Fixture mode runs without live LLM keys
- **GIVEN** golden cases with fixture/recorded expectations
- **WHEN** an operator runs the eval runner in fixture mode
- **THEN** the run completes without requiring production LLM API keys
- **AND** the CLI still prints an aggregate `PASS: X/Y` (or equivalent) summary

#### Scenario: Live mode hits a target API
- **GIVEN** a reachable API base URL and valid token(s)
- **WHEN** an operator runs the eval runner in live mode against that base URL
- **THEN** cases execute against the real HTTP surfaces under test
- **AND** failing cases are identified in the summary output

### Requirement: Golden IDs come from seed or fixtures
Golden cases that assert on note, chunk, or similar identifiers MUST obtain those IDs from a documented seed step OR avoid hard-coded environment-specific IDs by using fixture/recorded mode. The harness MUST NOT assume arbitrary UUIDs exist in a fresh environment.

#### Scenario: Operator can seed or use fixtures
- **GIVEN** a clean or unfamiliar target environment
- **WHEN** an operator follows `evals/README.md` to prepare a live or fixture run
- **THEN** they find either a documented seed procedure or fixture mode that does not require guessing IDs
- **AND** tenant-isolation cases remain runnable via dual tokens (live) or fixture responses

### Requirement: Eval import path is documented
`evals/README.md` MUST document how to run the runner with `src` importable (for example `PYTHONPATH=src` or `python -m …`) so operators do not hit ModuleNotFoundError when `evals/` lives outside `src/`.

#### Scenario: Fresh clone can invoke the runner
- **GIVEN** a developer has dependencies installed and is at the repo root
- **WHEN** they follow the documented run command in `evals/README.md`
- **THEN** the runner starts without an import-path failure for project modules under `src/`
