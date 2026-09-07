## Purpose

Portfolio packaging: stranger-test README pitch, honest metrics/demo claims, and architecture discoverability.

## Requirements

### Requirement: Root README presents a stranger-test pitch
The root `readme.md` MUST include: a one-sentence product pitch, stack summary, pointer to architecture documentation, and a “built” capability summary covering RAG, agent, workers/automation, and local Compose. When live URLs exist, they MUST be linked; until then placeholders or “pending deploy” MUST be explicit.

#### Scenario: New reader understands the product from README
- **GIVEN** a reader opens the root README with no prior context
- **WHEN** they read the pitch, stack, built table, and doc links
- **THEN** they can identify what DashNoteSystem is and which major AI surfaces exist
- **AND** they are directed to canonical architecture docs for depth

### Requirement: Metrics and demo evidence are honest
README (or clearly linked docs) MUST provide placeholders or filled values for eval pass rate and cost/latency notes. The project MUST NOT claim “production-ready” or “live demo” unless corresponding smoke/CI or live URL evidence exists. Demo video links MAY be external (Loom/YouTube) referenced from README.

#### Scenario: No false production claims
- **GIVEN** production smoke or live TLS URL is not yet verified
- **WHEN** a reader reviews README claims
- **THEN** the README does not assert an unverified live production deployment as complete
- **AND** any metrics section distinguishes documented measurements from TODOs

#### Scenario: Metrics section present
- **GIVEN** the portfolio baseline docs are updated
- **WHEN** a reader looks for quality/cost signals
- **THEN** they find an eval pass-rate field and a cost/latency field (filled or explicitly pending)

### Requirement: Architecture discoverability
README MUST link to existing system/AI documentation (e.g. `docs/documentation/system.md`, `docs/documentation/ai.md`, and/or UML docs) so reviewers can navigate tenancy and AI laws without hunting the tree.

#### Scenario: Architecture links resolve
- **GIVEN** the updated root README
- **WHEN** a reader follows the architecture documentation links
- **THEN** they reach in-repo docs that describe routing/tenancy and AI behavior

### Requirement: Ship-plan locks hiring path to blueprint8
`docs/ship-plan.md` MUST identify `docs/documentation/blueprint8.md` as the locked ship path for top-~10% (job gate) and top-~3–5% (Tier 1/2 deepeners). Day/phase checklists in ship-plan MUST NOT instruct operators to follow a contradictory default order.

#### Scenario: Ship-plan reader sees locked path
- **GIVEN** this change is complete
- **WHEN** a reader opens `docs/ship-plan.md`
- **THEN** they find an explicit lock/pointer to blueprint8
- **AND** Phase 2 depth items include HITL, Langfuse-depth evals, and measure→improve experiments consistent with blueprint8

### Requirement: Portfolio claims stay honest under Alive law
Portfolio packaging docs updated by this path MUST continue to forbid claiming live production or “production-ready” without smoke/live evidence, and MUST distinguish Tier 0 job-gate metrics from optional Tier 2 lab metrics.

#### Scenario: Metrics distinguish gate vs lab
- **GIVEN** README or ship-plan metrics sections after this change
- **WHEN** a reader looks for quality signals
- **THEN** eval pass-rate / cost-latency remain the job-gate signals
- **AND** any recall@k or faithfulness figures are labeled optional/nightly or pending when not measured

### Requirement: Failure-mode notes exist for demo and ops talk track
The repository MUST include operator-facing failure-mode notes covering at least empty retrieval, LLM/provider unavailable (e.g. 503 path), and embed lag / eventual consistency for search. Notes MUST be discoverable from runbook, interview talk track, or README links and MUST describe observable symptoms and recovery—not secret credentials.

#### Scenario: Operator finds empty-retrieval and LLM-down guidance
- **GIVEN** this change is complete
- **WHEN** an operator prepares a demo or incident talk track
- **THEN** they can find documented guidance for empty retrieval and LLM unavailable behavior
- **AND** embed lag / delayed search readiness is mentioned where relevant

### Requirement: Cost and latency table accepts local sample labeling
README (or clearly linked docs) MUST include a cost/latency table that can be filled from Langfuse export or a fixed local sample run. Until production smoke exists, filled values MUST be labeled as local/sample (not production SLO). The field MUST remain present when values are still pending.

#### Scenario: Local sample is honest
- **GIVEN** an operator records latency/cost from a local Langfuse or scripted sample
- **WHEN** the README table is updated
- **THEN** the environment is labeled local/sample
- **AND** the project does not present those numbers as verified production SLOs
