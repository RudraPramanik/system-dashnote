## ADDED Requirements

### Requirement: Harness fixture themes stay on thin PR CI without live keys
Thin PR CI MUST keep the Blueprint 9 harness fixture themes inside the merge-blocking pytest job (or an equivalent merge-blocking fixture step that needs no live LLM keys). The workflow MUST NOT add live LLM provider keys, production VPS credentials, or SSH so that harness grade proof can pass. Live jailbreak suites and LLM-as-judge jobs MUST NOT be added as required checks for merge.

#### Scenario: Harness themes covered by blocking pytest
- **GIVEN** thin CI runs `python -m pytest` (with its documented ignores) on pull requests
- **WHEN** the four designated harness fixture themes exist under `tests/ai/`
- **THEN** those themes are collected and executed by that blocking pytest job
- **AND** the job does not require a live LLM API key for them

#### Scenario: Nightly judges are not merge-required
- **GIVEN** an operator considers adding a live jailbreak or LLM-as-judge GitHub job
- **WHEN** they evaluate merge requirements for thin CI
- **THEN** such a job MUST NOT be a required merge check
- **AND** thin CI documentation or workflow comments MUST keep live/judge lanes labeled non-blocking if mentioned
