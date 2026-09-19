## ADDED Requirements

### Requirement: RAGAS operator extra resolves a Gemini-capable judge stack
The laptop-only RAGAS dependency file MUST pin versions that install a RAGAS release whose judge factory accepts a Google/Gemini client (or an equivalent documented Gemini wiring path used by the lab). The pin MUST NOT force an older release that only constructs an OpenAI-shaped default judge when the operator follows the documented `pip install -r evals/requirements-ragas.txt` path.

#### Scenario: Documented pip install yields Gemini-capable RAGAS
- **GIVEN** a clean operator environment following `evals/README.md`
- **WHEN** the operator installs `evals/requirements-ragas.txt`
- **THEN** the installed RAGAS stack can construct a Gemini judge with the dedicated lab credential
- **AND** construction MUST NOT fail solely because the factory rejects Google/Gemini provider parameters required by the lab script

### Requirement: Live RAGAS scoring completes after successful collection
When `evals/run_ragas.py --live` collects at least one question/answer/contexts row and `GEMINI_API_KEY_2` is set, the process MUST run the faithfulness and context-precision evaluation and print aggregate scores. It MUST exit zero on a successful evaluate path. It MUST NOT crash with a TypeError (or equivalent) from an unsupported judge-factory signature before printing scores.

#### Scenario: Collected rows produce printed metric aggregates
- **GIVEN** local Compose is reachable and a valid JWT is supplied
- **AND** `GEMINI_API_KEY_2` is set
- **AND** at least one retrieval golden yields a non-empty answer and context texts
- **WHEN** the operator runs the documented `--live` command
- **THEN** the CLI prints aggregate faithfulness and context precision (or equivalently named) scores
- **AND** the process exits with code 0

#### Scenario: Partial collection still scores remaining rows
- **GIVEN** some goldens are SKIPPED (e.g. chat HTTP error or empty retrieval)
- **AND** at least one row was collected
- **WHEN** scoring runs
- **THEN** evaluation proceeds on the collected rows
- **AND** skipped cases do not by themselves prevent score output
