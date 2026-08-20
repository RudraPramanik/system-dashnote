## ADDED Requirements

### Requirement: Eval blueprint locks runner modes fixture vs live
The eval blueprint MUST require the runner (and CI wiring) to distinguish deterministic/fixture mode from live API mode. PR CI MUST only execute fixture/deterministic cases and MUST NOT require live LLM keys or a full authenticated live stack to stay green. Live `--base-url` + token runs MUST be documented as operator/nightly.

#### Scenario: PR CI never requires live LLM
- **GIVEN** 8X.2.4 / CI vs live law
- **WHEN** an implementer wires evals into GitHub Actions
- **THEN** only fixture/deterministic cases are allowed as PR-blocking
- **AND** live mode remains an operator/nightly path

### Requirement: Eval blueprint defines trajectory scoring schema fields
The eval blueprint’s schema (8X.2.0) MUST define machine-checkable fields for agent trajectory cases, including at least: forbidden tools, required tools, and sequence mode (`exact` or `subset`). Vague “assert tool sequence” without these fields is insufficient.

#### Scenario: Forbid surprise create is expressible
- **GIVEN** the golden schema documentation
- **WHEN** an author writes the forbid-surprise-create case
- **THEN** they can express that `create_note` is forbidden without relying on prose-only expectations

### Requirement: Eval blueprint requires seed or fixture for entity IDs
The eval blueprint MUST require a strategy so golden `note_id` / `chunk_id` (and similar) references are either produced by a documented seed step or avoided via fixture/recorded mode. Goldens MUST NOT assume arbitrary IDs exist in a fresh environment without that strategy.

#### Scenario: Fresh env does not brick the harness
- **GIVEN** 8X.2.0–8X.2.2 guidance
- **WHEN** an operator runs the runner in a clean local stack or fixture mode
- **THEN** the blueprint documents how IDs are seeded or how fixture mode avoids needing them

### Requirement: Eval blueprint covers tenant dual-auth or fixture
Tenant-isolation goldens that compare two members/workspaces MUST specify either two real auth tokens/workspaces for live mode or an equivalent fixture/recorded path. The blueprint MUST NOT leave “member B must not see A’s note” as documentation-only.

#### Scenario: Isolation case is automatable
- **GIVEN** tenant_isolation goldens
- **WHEN** the runner executes the isolation theme
- **THEN** the case is runnable via dual tokens or fixture mode
- **AND** is not merely a README claim

### Requirement: Eval blueprint documents evals import path
The eval blueprint MUST document how to run the runner so shared schemas under `src/` are importable (e.g. `PYTHONPATH=src` or `python -m` from a documented working directory).

#### Scenario: README states import path
- **GIVEN** `evals/README.md` guidance in the blueprint
- **WHEN** an operator runs the CLI
- **THEN** they have documented steps that avoid ModuleNotFoundError for `src` packages

## MODIFIED Requirements

### Requirement: Eval blueprint defines ordered substages
The eval blueprint MUST define ordered substages covering at least: golden schema/folder laws (including runner modes, trajectory assert fields, and seed/fixture ID strategy), retrieval and tenant-isolation cases, a runner CLI with pass/fail summary and explicit fixture vs live support, at least five agent trajectory cases including forbid-surprise-create, and optional deterministic CI wiring with honest pass-rate documentation. Live LLM evaluation MUST NOT be required to green PR CI.

#### Scenario: Eval themes and agent minima
- **GIVEN** the eval blueprint
- **WHEN** an implementer plans the corpus
- **THEN** retrieval, tenant isolation, and ≥5 agent trajectory cases (including forbid surprise create) are required themes
- **AND** PR CI is instructed to avoid mandatory live LLM calls

#### Scenario: Schema precedes corpus fill
- **GIVEN** the substage order
- **WHEN** an implementer reaches retrieval goldens
- **THEN** schema/mode/seed contracts from the first substage already exist so cases are writable against a known contract
