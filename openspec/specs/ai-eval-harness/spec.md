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
Planning documentation for the eval program (at minimum `docs/documentation/blueprint8.md`, and `evals/README.md` when the harness exists) MUST describe post-C-gate thickeners: Langfuse-native datasets/experiments as the preferred judge/experiment path, optional recall@k or MRR on goldens, optional faithfulness/answer-relevancy as operator/nightly, and an EXPERIMENTS / before-after record. These thickeners MUST NOT replace the golden JSONL + `run_eval.py` C-gate harness, and MUST NOT require live LLM judges to green PR CI.

#### Scenario: Operator finds preferred eval stack
- **GIVEN** blueprint8 (and evals README when present)
- **WHEN** an operator plans quality work after C-gate
- **THEN** Langfuse-native experiments/judges are documented as the primary thickener
- **AND** RAGAS is optional nightly if mentioned
- **AND** PR CI remains fixture/deterministic-only for blocking gates

#### Scenario: C-gate remains the hire minimum
- **GIVEN** the documented eval program
- **WHEN** an operator checks the hire-ready eval minimum
- **THEN** ≥10 retrieval/tenant cases, pass/fail CLI summary, tenant isolation automation, and honest pass-rate docs remain required
- **AND** faithfulness or recall@k are not required to claim the C-gate
