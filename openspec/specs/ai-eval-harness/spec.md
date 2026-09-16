## Purpose

Golden eval corpus and CLI runner for retrieval quality and tenant isolation against a target API.

## Requirements

### Requirement: Golden eval corpus exists
The repository MUST include an `evals/golden/` corpus with at least ten cases covering retrieval relevance and tenant isolation. Cases MUST be machine-readable (e.g. JSONL) and documented enough for an operator to run them against a target API.

#### Scenario: Corpus meets minimum size and themes
- **GIVEN** the repository at this change’s completion
- **WHEN** an operator inspects `evals/golden/`
- **THEN** there are at least ten cases total
- **AND** the set includes retrieval cases and at least one tenant-isolation case

### Requirement: Eval runner prints pass/fail summary
The repository MUST provide `evals/run_eval.py` (or equivalent CLI) that executes the golden set against a configurable base URL and auth token, and prints a clear pass/fail summary (e.g. `PASS: 8/10`) with failing case identities.

#### Scenario: Operator runs eval CLI
- **GIVEN** a reachable API and a valid auth token for an eval workspace
- **WHEN** the operator runs the eval runner with base URL and token
- **THEN** the CLI prints an aggregate pass/fail count
- **AND** lists or identifies any failing cases

### Requirement: Tenant isolation is enforced in evals
The golden set MUST include an automated check that a `member` role JWT cannot retrieve another user’s private note content via the search/RAG surface. Workspace identity MUST come from JWT context (`wid`), never from caller-supplied workspace query/body fields.

#### Scenario: Member cannot retrieve peer private note
- **GIVEN** note N is private and owned by user A in workspace W
- **AND** user B is a `member` of W and is not the owner of N
- **WHEN** an eval runs search or RAG as user B for content unique to N
- **THEN** the eval marks the case as pass only if N’s private content is not returned to B

#### Scenario: Workspace id not taken from request input on search
- **GIVEN** a search or test-search request
- **WHEN** the client omits or forges a workspace identifier in query or body
- **THEN** retrieval still scopes exclusively to the JWT workspace
- **AND** cross-tenant results are not returned

### Requirement: Eval pass rate is documentable
Operators MUST be able to record the eval pass rate in project documentation (README or evals README). The documented rate MUST reflect an actual runner summary, including rates below 100% when failures exist.

#### Scenario: Pass rate recorded from runner output
- **GIVEN** a completed eval runner execution with summary `PASS: X/Y`
- **WHEN** portfolio or eval docs are updated for the baseline
- **THEN** the documented pass rate matches that summary (honest if X < Y)

### Requirement: Post-C-gate eval thickeners are documented without replacing the harness
Planning documentation for the eval program (at minimum `docs/documentation/blueprint8.md`, and `evals/README.md` when the harness exists) MUST describe post-C-gate thickeners: Langfuse-native datasets/experiments as the preferred in-product judge/experiment path, optional recall@k or MRR on goldens, a runnable operator/nightly RAGAS lab (faithfulness and context metrics, dedicated judge credential, off VPS and off PR CI), and an EXPERIMENTS / before-after record. These thickeners MUST NOT replace the golden JSONL + `run_eval.py` C-gate harness, and MUST NOT require live LLM judges or RAGAS to green PR CI. `evals/README.md` MUST link to the EXPERIMENTS document. After this change the Langfuse dataset + sampled faithfulness judge MUST remain documented as an existing operator/nightly procedure, and the RAGAS lab MUST be documented as an existing local/nightly procedure (not only a future preference).

#### Scenario: Operator finds preferred eval stack
- **GIVEN** blueprint8 (and evals README when present)
- **WHEN** an operator plans quality work after C-gate
- **THEN** Langfuse-native experiments/judges are documented as the primary in-product thickener
- **AND** RAGAS is documented as a runnable local/nightly lab (not VPS, not CI)
- **AND** PR CI remains fixture/deterministic-only for blocking gates

#### Scenario: C-gate remains the hire minimum
- **GIVEN** the documented eval program
- **WHEN** an operator checks the hire-ready eval minimum
- **THEN** ≥10 retrieval/tenant cases, pass/fail CLI summary, tenant isolation automation, and honest pass-rate docs remain required
- **AND** faithfulness, RAGAS scores, or recall@k are not required to claim the C-gate

#### Scenario: EXPERIMENTS is linked from evals README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find a link or pointer to the EXPERIMENTS before-after record

#### Scenario: Operator README names the runnable judge procedures
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find how to run the Langfuse dataset/faithfulness operator path
- **AND** they find how to set up and run the RAGAS lab (extra install, dedicated judge env var, command)
- **AND** they are told PR CI and VPS deploy do not require those paths

### Requirement: Operator RAGAS lab is runnable off the product path
The eval program MUST provide an operator-runnable RAGAS (or equivalent RAG metric) lab that scores question, generated answer, and retrieved context. The lab MUST use a dedicated judge credential distinct from the embeddings / chat-fallback Gemini key. The lab MUST be invocable from documentation without installing the metric library into the API runtime image. Fixture `evals/run_eval.py --mode fixture` MUST remain the blocking eval gate and MUST still complete without the judge credential or the RAGAS extra.

#### Scenario: Operator can run the lab without changing CI
- **GIVEN** the dedicated judge credential is set in the operator environment
- **AND** the documented RAGAS extra is installed in that environment
- **WHEN** the operator runs the documented lab procedure
- **THEN** the CLI prints aggregate metric scores (at least faithfulness, and context precision or context recall)
- **AND** GitHub Actions PR CI still runs only fixture evals and does not invoke the lab

#### Scenario: Missing judge credential fails closed
- **GIVEN** the dedicated judge credential is unset or blank
- **WHEN** the operator runs the lab
- **THEN** the process exits non-zero with a message that names the required env var
- **AND** it MUST NOT fall back to the embeddings / chat-fallback Gemini key

#### Scenario: Hot path does not wait on RAGAS
- **GIVEN** a production `/ai/chat` or `/ai/agent` request
- **WHEN** the request returns an answer or `approval_required`
- **THEN** response latency MUST NOT include a RAGAS or LLM-as-judge completion for that turn

### Requirement: RAGAS lab stays off VPS and out of product config
The RAGAS lab MUST NOT be deployed on the VPS, MUST NOT be added to Docker Compose API or worker images, and MUST NOT be loaded by API Settings. The judge credential placeholder MAY appear in `.env.example` for local operators. Product Settings, Compose, deploy scripts, and documented VPS `.env` MUST NOT require that credential.

#### Scenario: VPS deploy artifacts ignore the judge key
- **GIVEN** this change is complete
- **WHEN** an operator inspects Compose, API Settings, and VPS deploy env examples
- **THEN** the dedicated judge credential is absent from those product surfaces
- **AND** the API still starts without it

#### Scenario: Example env documents the operator key only
- **GIVEN** this change is complete
- **WHEN** an operator opens `.env.example`
- **THEN** they find an empty `GEMINI_API_KEY_2` placeholder labeled as the RAGAS/judge key
- **AND** comments MUST state it is local/operator-only and MUST NOT be used for embeddings

### Requirement: Live RAGAS collection keeps JWT tenancy
When the lab collects answers or contexts from a live API, it MUST authenticate with a JWT and MUST scope retrieval to that token’s workspace (`wid`). It MUST NOT accept a workspace identifier from query or body for scoping. Tenant-isolation goldens remain the C-gate; the RAGAS lab MUST NOT claim to replace them.

#### Scenario: Live collection uses JWT workspace only
- **GIVEN** the operator runs the lab against a live base URL with a JWT
- **WHEN** the lab requests chat or search for a golden query
- **THEN** workspace scoping comes from the JWT only
- **AND** forged workspace fields MUST NOT expand retrieval

### Requirement: RAGAS scores are lab records not SLOs
Operators MUST record at least one dated RAGAS lab result in `docs/EXPERIMENTS.md` with environment labeled `lab` (or `live-local`). The record MUST NOT present those scores as production SLOs. The golden JSONL harness remains the C-gate.

#### Scenario: EXPERIMENTS has an honest RAGAS row
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/EXPERIMENTS.md`
- **THEN** they find a RAGAS (or equivalent) loop that names environment `lab` or `live-local`
- **AND** the text MUST NOT call the scores a production SLO

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
