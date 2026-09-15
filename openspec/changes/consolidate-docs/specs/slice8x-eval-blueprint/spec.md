## ADDED Requirements

### Requirement: Eval operator truth is evals README
Operators MUST find eval harness usage in `evals/README.md` (and EXPERIMENTS for measure→improve). The repository MUST NOT require `docs/documentation/blueprint/slice8_eval.md` to exist.

#### Scenario: Operator does not need slice8_eval.md
- **GIVEN** this change is complete
- **WHEN** an operator wants to run fixture or live evals
- **THEN** they can do so from `evals/README.md`
- **AND** they are not required to open `slice8_eval.md`

## REMOVED Requirements

### Requirement: Slice 8X eval detail blueprint exists
**Reason**: The golden harness already shipped; the Composer prompt file is leftover.
**Migration**: Use `evals/README.md` and the `ai-eval-harness` spec.

### Requirement: Eval blueprint defines ordered substages
**Reason**: Corpus, runner, and trajectory cases already exist under `evals/`.
**Migration**: Extend the harness via `ai-eval-harness`, not a restored prompt file.

### Requirement: Eval blueprint preserves tenancy and chat≠agent
**Reason**: Those laws remain in canonical AI docs and eval specs.
**Migration**: Follow `docs/documentation/ai.md` and `ai-eval-harness`.

### Requirement: Eval blueprint locks runner modes fixture vs live
**Reason**: Fixture vs live is documented in `evals/README.md`.
**Migration**: Use the evals README.

### Requirement: Eval blueprint defines trajectory scoring schema fields
**Reason**: Schema lives with the golden corpus / runner.
**Migration**: Inspect `evals/` artifacts.

### Requirement: Eval blueprint requires seed or fixture for entity IDs
**Reason**: Seed/fixture strategy is encoded in the harness, not a prompt file.
**Migration**: Follow `evals/README.md`.

### Requirement: Eval blueprint covers tenant dual-auth or fixture
**Reason**: Tenant cases are in the golden set / `ai-eval-harness`.
**Migration**: Use the eval harness docs.

### Requirement: Eval blueprint documents evals import path
**Reason**: Import/run path is in `evals/README.md`.
**Migration**: Use that README.
