## ADDED Requirements

### Requirement: First implementation phase after the blueprint is L0
The lifecycle blueprint MUST name L0 (deterministic fixture / golden contract) as the first implementation phase after the docs-only blueprint. That phase MUST close the fixture runner, goldens, CI-safe scoring tests, and an honest recorded fixture pass rate. It MUST NOT require shipping DeepEval, answer goldens, or `run_quality.py`. Later phases (RAG answer quality, thresholds, style work, agent quality) remain separate changes.

#### Scenario: This change does not ship the judge suite
- **GIVEN** the L0 implementation change is complete
- **WHEN** an operator inspects `evals/`
- **THEN** `evals/run_eval.py --mode fixture` is the implemented gate
- **AND** a DeepEval quality runner is not required to exist
- **AND** the blueprint still lists L2 as a later phase

### Requirement: Blueprint documents NVIDIA NIM as the Gemini 429 hatch
The lifecycle blueprint MUST state that L0 fixture evals need no LLM keys, and MUST document NVIDIA NIM (a different free/catalog model on the product candidate list) as the escape hatch when Gemini rate-limit / 429 blocks later live collection or product chat. The hatch MUST NOT put an LLM-as-judge on the `/ai/chat` or `/ai/agent` hot path, and MUST NOT make live keys a PR CI requirement.

#### Scenario: Operator can place quota vs fixture
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator hits Gemini 429 during live collection
- **THEN** the blueprint tells them to use NVIDIA NIM with a different free model
- **AND** it tells them L0 fixture CI still runs without those keys
- **AND** it does not instruct them to await a judge on `/ai/chat` or `/ai/agent`

## MODIFIED Requirements

### Requirement: Blueprint names a follow-on implementation sequence
The lifecycle blueprint MUST list ordered follow-on phases so this repository does not implement the whole program in one change. At minimum: (0) the blueprint document, (1) L0 fixture-gate close-out (this class of change), (2) RAG answer goldens + DeepEval quality CLI, (3) thresholds / baseline regression, (4) style-driven generator work, (5) agent quality suite. Each later phase MUST be a separate change unless an operator explicitly expands scope.

#### Scenario: Apply of this change does not ship DeepEval
- **GIVEN** this change is complete
- **WHEN** an operator inspects `evals/`
- **THEN** `evals/BLUEPRINT.md` exists
- **AND** a DeepEval quality runner is not required to exist yet
- **AND** the blueprint names L0 as the first implementation phase and L2 as a later phase
