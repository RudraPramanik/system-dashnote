## Purpose

Defines the authoritative Blueprint 8 ship path: Alive product law, job-gate spine, Tier 1/2 quality deepeners, GraphRAG intro as non-goal productization, and consistency with existing `blueprint/` detail docs and `ship-plan.md`.

## Requirements

### Requirement: Blueprint8 document is the operator-default ship path
The repository MUST include a non-empty `docs/documentation/blueprint8.md` that identifies itself as the operator-default ship path for hiring readiness and AI-engineering depth. Operators MUST be instructed to follow blueprint8 first; detail documents under `docs/documentation/blueprint/` remain executable and MUST stay consistent with blueprint8 (no contradictory default order).

#### Scenario: Operator opens blueprint8
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/documentation/blueprint8.md`
- **THEN** the file is non-empty
- **AND** it states that it is the default path to follow
- **AND** it points to existing detail blueprints under `docs/documentation/blueprint/` for executable substages

#### Scenario: Detail blueprints are not orphaned
- **GIVEN** blueprint8 is the default
- **WHEN** an operator needs Slice 8X.2 evals or 8X.3 HITL prompts
- **THEN** blueprint8 links to `blueprint/slice8_eval.md` and `blueprint/slice8_hitl.md` (or equivalent)
- **AND** those detail docs remain valid Composer-ready blueprints

### Requirement: Alive law keeps API frontend and AI shippable
Blueprint8 MUST define an Alive law: the product (API + AI surfaces + frontend demo path) MUST remain deployable and demoable; Tier-2 or lab work that is hostile to a small VPS MUST run local, fixture, or nightly and MUST NOT be required on the production compose path to claim the job gate.

#### Scenario: VPS-hostile work is segregated
- **GIVEN** an operator reads the Alive / local-vs-VPS section
- **WHEN** they plan a heavy eval judge, local reranker, or similar lab item
- **THEN** blueprint8 classifies it as local/nightly/fixture-only unless explicitly slim enough for production
- **AND** it forbids making the live demo depend on that lab item

#### Scenario: Chat and agent coexistence preserved
- **GIVEN** the Alive / architecture constraints in blueprint8
- **WHEN** an implementer follows the path
- **THEN** `/ai/chat*` and `/ai/agent*` MUST both remain; neither replaces the other

### Requirement: Job gate spine is mandatory before claiming hire-ready
Blueprint8 MUST define a Tier 0 / job-gate spine covering live production proof, frontend stranger-demo path, evaluation C-gate (retrieval + tenant isolation + documented pass rate), and portfolio packaging (README metrics, demo evidence). Claiming job-search readiness MUST require that spine.

#### Scenario: Job gate themes are listed
- **GIVEN** the Tier 0 section in blueprint8
- **WHEN** an implementer checks hire-ready criteria
- **THEN** live/smoke proof, frontend demo path, eval pass-rate documentation, and portfolio packaging are all listed
- **AND** GraphRAG productization is not required for the job gate

### Requirement: Tier 1 and Tier 2 define the ahead-of-most track
Blueprint8 MUST define Tier 1 (production-valid deepeners: HITL on agent mutations, Langfuse retrieval-depth observability, cost/latency evidence, fixture evals in CI, agent trajectory goldens, failure-mode notes) and Tier 2 (local/nightly thickeners: recall@k or MRR, faithfulness/answer-relevancy judges via Langfuse-native experiments with optional RAGAS nightly, EXPERIMENTS.md before/after, optional hybrid/rerank lab). Tier 1+2 MUST be framed as the top-percentile track without blocking Tier 0.

#### Scenario: HITL and Langfuse are Tier 1 centerpieces
- **GIVEN** the Tier 1 section
- **WHEN** an operator reads centerpiece deepeners
- **THEN** human-in-the-loop before agent create/update side effects is listed
- **AND** Langfuse enrichment beyond chunk counts (e.g. retrieved identities and scores in traces/scores) is listed
- **AND** Langfuse-native datasets/experiments are preferred over replacing the custom golden harness

#### Scenario: Tier 2 is not PR-blocking by default
- **GIVEN** the Tier 2 section
- **WHEN** CI vs nightly rules are read
- **THEN** LLM-as-judge / live faithfulness runs are operator or nightly
- **AND** PR CI remains fixture/deterministic only for eval gating

### Requirement: GraphRAG appears as a short introduction only
Blueprint8 MUST include a short GraphRAG introduction explaining the idea (entities/relations over notes) and explicit deferral: GraphRAG MUST NOT be required for job gate or Tier 1; productization (e.g. Neo4j) remains optional/blocked until a later authorized change after production gate health.

#### Scenario: GraphRAG intro without productization mandate
- **GIVEN** the GraphRAG section in blueprint8
- **WHEN** an implementer considers adding Neo4j
- **THEN** they are instructed that blueprint8 only introduces the concept
- **AND** they MUST NOT treat GraphRAG as part of the default ship path

### Requirement: Ship-plan locks to blueprint8
`docs/ship-plan.md` MUST be updated so Phase 1 (top ~10%) and Phase 2 (top ~3–5%) follow blueprint8’s Tier 0 then Tier 1/2 map, and MUST link to `docs/documentation/blueprint8.md` as the locked path.

#### Scenario: Ship-plan points at blueprint8
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/ship-plan.md`
- **THEN** they find an explicit pointer that blueprint8 is the locked ship path
- **AND** Phase 2 items align with Tier 1/2 deepeners (HITL, Langfuse depth, recall/faithfulness, experiments) rather than contradicting them
