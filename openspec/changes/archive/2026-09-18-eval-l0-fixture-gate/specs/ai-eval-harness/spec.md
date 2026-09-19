## ADDED Requirements

### Requirement: L0 fixture evals complete without LLM keys
The golden fixture runner (`evals/run_eval.py --mode fixture`) MUST execute retrieval, tenant-isolation, and agent-trajectory cases from recorded fixtures without calling a live LLM provider. It MUST NOT require `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, or `NVIDIA_NIM_API_KEY`. PR CI MUST continue to run this fixture mode as the blocking eval gate and MUST NOT invoke live API mode or an LLM-as-judge suite.

#### Scenario: Fixture run with empty provider keys
- **GIVEN** the repository goldens and fixtures under `evals/`
- **AND** no Gemini or NVIDIA NIM keys are set in the process environment
- **WHEN** an operator or CI runs `evals/run_eval.py --mode fixture`
- **THEN** the process scores the fixture cases and prints an aggregate `PASS: X/Y`
- **AND** it MUST NOT fail because a provider key is missing
- **AND** it MUST NOT call a live LLM HTTP API

#### Scenario: PR CI stays fixture-only
- **GIVEN** GitHub Actions PR CI
- **WHEN** the eval step runs
- **THEN** it uses fixture mode only
- **AND** it does not require live tokens, judge extras, or NVIDIA NIM

### Requirement: L0 scoring is covered by CI-safe tests
The repository MUST include automated tests that exercise fixture scoring for retrieval markers, tenant isolation (leaked markers fail), and agent trajectory constraints (`required_tools`, `forbidden_tools`, `sequence_mode`) without live HTTP or LLM keys. Those tests MUST run as part of the existing pytest CI job.

#### Scenario: Marker miss fails a retrieval case
- **GIVEN** a retrieval golden that expects a content marker
- **AND** the recorded fixture payload omits that marker
- **WHEN** the scoring tests run
- **THEN** that case is reported as fail
- **AND** no live API is contacted

#### Scenario: Forbidden tool fails a trajectory case
- **GIVEN** a trajectory golden that forbids `create_note`
- **AND** the recorded tool list includes `create_note`
- **WHEN** the scoring tests run
- **THEN** that case is reported as fail

#### Scenario: Tenant leak fails isolation
- **GIVEN** a tenant-isolation golden with `expect_no_content_markers`
- **AND** the recorded payload contains a forbidden marker
- **WHEN** the scoring tests run
- **THEN** that case is reported as fail

### Requirement: L0 apply records an honest fixture pass rate
Operators MUST be able to run the fixture runner locally after this change and record the actual `PASS: X/Y` in `evals/README.md`. The documented rate MUST match that run, including rates below 100% when failures exist. A previous dated row MUST NOT be reused as proof that this change works.

#### Scenario: Fresh fixture summary is recorded
- **GIVEN** this change’s apply has run `evals/run_eval.py --mode fixture`
- **WHEN** an operator opens `evals/README.md`
- **THEN** the latest recorded fixture row matches that run’s `PASS: X/Y`
- **AND** the text does not claim success from an older run

### Requirement: Operator docs name NVIDIA NIM as the Gemini quota hatch for later live layers
`evals/README.md` MUST state that L0 fixture mode needs no LLM keys, and MUST tell operators that if a later live collection or product chat path hits Gemini rate-limit / 429, they MUST use NVIDIA NIM with a different free/catalog model (via the product candidate list) rather than waiting on Gemini quota. That hatch MUST NOT be required to green L0 fixture CI.

#### Scenario: Operator finds the quota hatch without needing it for L0
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find that fixture mode needs no Gemini or NVIDIA keys
- **AND** they find that Gemini 429 is an operator/live concern addressed by NVIDIA NIM (a different free model), not by skipping L0
- **AND** they are told PR CI still runs fixture-only
