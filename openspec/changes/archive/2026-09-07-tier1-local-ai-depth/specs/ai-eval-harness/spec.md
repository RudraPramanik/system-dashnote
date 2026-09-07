## ADDED Requirements

### Requirement: Agent trajectory golden corpus exists
The `evals/golden/` corpus MUST include at least five agent trajectory cases covering tool-use expectations. Cases MUST support constraints such as `required_tools`, `forbidden_tools`, and `sequence_mode` (`exact` or `subset`). At least one case MUST forbid surprise note creation (e.g. `create_note` in `forbidden_tools` when the user did not ask to create).

#### Scenario: Trajectory set meets minimum
- **GIVEN** this change is complete
- **WHEN** an operator inspects agent trajectory goldens
- **THEN** there are at least five trajectory cases
- **AND** at least one case fails if the agent unexpectedly calls `create_note`

#### Scenario: Fixture mode supports trajectory without live LLM
- **GIVEN** recorded fixtures for trajectory cases
- **WHEN** the operator runs `evals/run_eval.py --mode fixture` including trajectory cases
- **THEN** the runner evaluates tool constraints without requiring live LLM API keys

### Requirement: Trajectory results appear in the eval summary
The eval runner MUST include trajectory cases in the aggregate `PASS: X/Y` summary and identify failing case ids when tool constraints are violated.

#### Scenario: Forbidden tool fails the case
- **GIVEN** a trajectory case that forbids `create_note`
- **WHEN** the observed tool sequence includes `create_note`
- **THEN** that case is marked fail in the runner output
