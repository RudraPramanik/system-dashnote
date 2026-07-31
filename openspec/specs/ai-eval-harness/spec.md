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
