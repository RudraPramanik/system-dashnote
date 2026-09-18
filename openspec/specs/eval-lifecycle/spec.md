## Purpose

Defines the production-grade eval program for DashNoteSystem: a modular `evals/` lifecycle, layered gates (fixture CI, live contract, LLM-as-judge quality, production observability), and an operator-facing blueprint that later implementation changes MUST follow.

## Requirements

### Requirement: Eval lifecycle blueprint exists under evals
The repository MUST include a single canonical eval lifecycle blueprint at `evals/BLUEPRINT.md`. The document MUST be the operator-facing source of truth for the full eval program (layers, data, metrics, CLI, placement, and phased rollout). It MUST NOT be a Cursor-prompt rewrite of `docs/documentation/blueprint/slice8_eval.md`.

#### Scenario: Operator finds the lifecycle blueprint
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/BLUEPRINT.md`
- **THEN** the file is non-empty
- **AND** it identifies itself as the canonical eval lifecycle for this repo
- **AND** it distinguishes itself from the Slice 8X.2 C-gate Cursor prompts

#### Scenario: README points at the blueprint
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find a link to `evals/BLUEPRINT.md`
- **AND** they can tell C-gate fixture commands from the planned judge-suite program

### Requirement: Blueprint documents four eval layers
The lifecycle blueprint MUST describe four distinct layers and MUST state which layer is allowed in PR CI, which runs local/pre-deploy, and which runs in production serving:

1. Deterministic fixture / golden contract evals
2. Live API contract evals against a real stack
3. LLM-as-judge answer-quality evals on a frozen dataset
4. Production observability (traces, user feedback, health metrics) that MUST NOT block request latency with a judge

#### Scenario: Operator can place each layer
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator plans where to run a new eval
- **THEN** they can map it to one of the four layers
- **AND** they are told PR CI MUST stay deterministic/fixture-only
- **AND** they are told LLM-as-judge MUST stay off the `/ai/chat` and `/ai/agent` hot path
- **AND** they are told production serving MUST NOT require the judge suite to return answers

### Requirement: All eval code and datasets live under evals
Future eval runners, extras, goldens, fixtures, and local reports for this program MUST live under the repository `evals/` tree. Product API, worker, and Compose images MUST NOT gain the judge extra as a runtime dependency. Eval data MUST NOT be stored as the sole copy under `src/`.

#### Scenario: Operator looks for eval artifacts
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator searches for goldens, judge extras, or the quality CLI
- **THEN** the blueprint locates them under `evals/`
- **AND** it forbids adding the judge library to the API image or VPS as a serving dependency

### Requirement: Blueprint specifies a single quality CLI
The lifecycle blueprint MUST specify one operator command (a single runner file under `evals/`) that, when implemented, collects RAG answers from a target API and prints LLM-as-judge scores to the terminal, including at least aggregate correctness, completeness, and style, plus collected `n`, SKIP counts, and NaN/fail-closed behavior. This change MUST document that CLI; it MUST NOT require the command to exist yet.

#### Scenario: Operator knows the intended one-shot run
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator reads the CLI section
- **THEN** they find one planned command that collects and scores
- **AND** they find the required terminal outputs (per-metric scores, `n`, SKIPs, NaN handling)
- **AND** they are told the command is a later phase if it is not implemented yet

### Requirement: Blueprint defines RAG-first then agent phases
The lifecycle blueprint MUST order work so RAG `/ai/chat` answer evaluation is implemented before agent `/ai/agent` evaluation. Chat and agent MUST remain separate surfaces. Agent trajectory fixture goldens already in the C-gate MUST remain; they MUST NOT be treated as the DeepEval answer suite.

#### Scenario: Implementer does not start with agent judge
- **GIVEN** the lifecycle blueprint phase list
- **WHEN** an implementer plans the first judge-suite change
- **THEN** the first quality-suite phase is RAG answers on `/ai/chat`
- **AND** agent LLM-as-judge is listed as a later phase
- **AND** `/ai/chat` is not replaced by `/ai/agent` to simplify evals

### Requirement: Blueprint defines answer-quality metrics and gates
The lifecycle blueprint MUST define answer-quality metrics of correctness, completeness, and style scored by an LLM judge against frozen expected answers or checklists. Correctness and completeness MUST be described as hard gates for the pre-deploy/nightly suite. Style MUST be included in the suite even when scores are expected to start low, and MUST be described as a generator-improvement lever rather than a vanity metric. Scores MUST NOT be labeled production SLOs.

#### Scenario: Style is measured before the generator is polished
- **GIVEN** the metrics section of the lifecycle blueprint
- **WHEN** an operator reads gate policy
- **THEN** correctness and completeness are hard gates for the quality suite
- **AND** style is always reported
- **AND** a low initial style score is an allowed honest outcome, not a reason to omit the metric

#### Scenario: Scores are lab or pre-deploy records
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator records a judge-suite run
- **THEN** they are instructed to label environment `lab` or `pre-deploy`
- **AND** they are forbidden from calling those scores a production SLO

### Requirement: Blueprint defines golden dataset lifecycle
The lifecycle blueprint MUST define an answer-golden schema covering at least: stable case id, query, expected answer or fact checklist, optional style notes, and seed or fixture strategy so entity IDs are not assumed in a fresh environment. Initial goldens MAY be AI-drafted. The blueprint MUST require human curation over time and MUST warn about teacher bias when the same model family writes goldens and generates answers.

#### Scenario: Author can write an answer golden from the schema
- **GIVEN** the golden-schema section
- **WHEN** an author adds a RAG answer case
- **THEN** they have documented fields for id, query, and expected output or checklist
- **AND** they are told not to hard-code environment-only note IDs without seed or fixture

#### Scenario: Synthetic goldens are honest
- **GIVEN** the data-lifecycle section
- **WHEN** an operator describes the corpus in docs or interviews
- **THEN** the blueprint instructs them to call v0 goldens AI-drafted and later curated
- **AND** it warns that same-family teacher/generator pairs can inflate correctness

### Requirement: Live quality collection keeps JWT tenancy
The lifecycle blueprint MUST require that live collection for the quality suite authenticates with a JWT and scopes retrieval to that token’s workspace (`wid`). It MUST NOT accept a workspace identifier from query or body for scoping. Tenant-isolation C-gate goldens MUST remain the isolation proof; the judge suite MUST NOT claim to replace them.

#### Scenario: Live judge collection is workspace-scoped
- **GIVEN** the tenancy section of the lifecycle blueprint
- **WHEN** a later change implements live collection
- **THEN** the documented contract is JWT `wid` only
- **AND** forged workspace fields MUST NOT expand retrieval
- **AND** tenant-isolation goldens remain the C-gate

### Requirement: Judge suite fails closed and reports honesty fields
The lifecycle blueprint MUST require the future quality CLI to exit non-zero when zero rows are collected or when required metrics are all NaN / non-numeric. It MUST forbid fabricating scores. Every recorded run MUST include `n`, SKIP reasons, and NaN notes. The judge credential MUST be distinct from the product embeddings / chat-fallback key, and MUST NOT fall back to that product key.

#### Scenario: Empty collection is not a successful score
- **GIVEN** the fail-closed section
- **WHEN** collection yields zero scored rows
- **THEN** the documented CLI behavior is non-zero exit
- **AND** aggregate metric scores are not printed as a successful run

#### Scenario: Dedicated judge key only
- **GIVEN** the secrets section
- **WHEN** the judge key is unset
- **THEN** the documented behavior is fail-closed naming the judge env var
- **AND** product Gemini MUST NOT be used as a fallback

### Requirement: Blueprint names a follow-on implementation sequence
The lifecycle blueprint MUST list ordered follow-on phases so this repository does not implement the whole program in one change. At minimum: (0) the blueprint document, (1) L0 fixture-gate close-out (this class of change), (2) RAG answer goldens + DeepEval quality CLI, (3) thresholds / baseline regression, (4) style-driven generator work, (5) agent quality suite. Each later phase MUST be a separate change unless an operator explicitly expands scope.

#### Scenario: Apply of this change does not ship DeepEval
- **GIVEN** this change is complete
- **WHEN** an operator inspects `evals/`
- **THEN** `evals/BLUEPRINT.md` exists
- **AND** a DeepEval quality runner is not required to exist yet
- **AND** the blueprint names L0 as the first implementation phase and L2 as a later phase

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

### Requirement: Second implementation phase after L0 is L1 live contract
The lifecycle blueprint MUST name L1 (live API contract against Compose or staging) as the second implementation phase after L0 fixture-gate close-out. That phase MUST close the live runner path for retrieval/tenant goldens shared with L0, operator docs for JWT live runs, the NVIDIA NIM Gemini-429 hatch for the live stack, and an honest recorded live `PASS: X/Y`. It MUST NOT require shipping DeepEval, answer goldens, or `run_quality.py`. PR CI MUST remain L0 fixture-only. Later phases (RAG answer quality, thresholds, style work, agent quality) remain separate changes.

#### Scenario: This change does not ship the judge suite
- **GIVEN** the L1 implementation change is complete
- **WHEN** an operator inspects `evals/`
- **THEN** `evals/run_eval.py --mode live` is the implemented live contract
- **AND** a DeepEval quality runner is not required to exist
- **AND** the blueprint still lists L2 as a later phase
- **AND** PR CI still runs fixture mode only

#### Scenario: Blueprint roadmap order is L0 then L1 then L2
- **GIVEN** the lifecycle blueprint phased roadmap
- **WHEN** an implementer plans the next eval change after L0
- **THEN** L1 live contract is the named next phase
- **AND** L2 LLM-as-judge is listed after L1

### Requirement: Blueprint documents L0/L1 alignment
The lifecycle blueprint MUST state that L0 fixture mode and L1 live mode share the same golden corpus and scoring contract for eligible cases. Fixtures are the recorded responses for CI; live mode proves the same markers and isolation against a real API. Trajectory goldens MAY remain fixture-primary. The blueprint MUST NOT present L0 and L1 as unrelated corpora.

#### Scenario: Operator sees one contract two modes
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator reads the L0/L1 layer descriptions
- **THEN** they are told both modes use the same goldens and scoring for eligible cases
- **AND** they are told L0 is the PR CI recorded form and L1 is the live proof
