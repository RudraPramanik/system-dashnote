## MODIFIED Requirements

### Requirement: L2 quality CLI collects chat answers and scores with an LLM judge
The repository MUST provide `evals/run_quality.py` (and a laptop-only quality requirements file) that loads the RAG answer goldens, authenticates with a JWT against a configurable base URL, calls `POST /ai/chat` with message-only scoping (JWT `wid`), collects `actual_output` and retrieval context when present, and scores with LLM-as-judge metrics for correctness, completeness, and style. Correctness and completeness MUST enforce documented hard floors. Style MUST always be reported (loose or no floor allowed at first). The runner MUST NOT import the judge library from `evals/run_eval.py`. The quality extra MUST NOT be added to API, worker, Compose serving images, or VPS as a runtime dependency.

#### Scenario: Operator runs the quality CLI
- **GIVEN** a reachable API, a valid JWT, the dedicated judge credential, and the quality extra installed on the laptop
- **WHEN** the operator runs `evals/run_quality.py` with base URL and token
- **THEN** the CLI prints environment label, judge model, per-metric aggregates, collected `n`, and SKIP count/reasons
- **AND** exit is non-zero when hard floors for correctness or completeness are missed on a scored run with `n > 0`

#### Scenario: SKIP on bad collection rows
- **GIVEN** a case whose live chat returns non-200, empty answer, empty retrieval, HTTP client timeout, or other request-transport failure
- **WHEN** the quality CLI processes that case
- **THEN** the case is counted as SKIP with a reason
- **AND** it is not scored as a successful judge row

## ADDED Requirements

### Requirement: L2 live collection survives chat timeouts
The quality CLI MUST catch HTTP client timeouts and other request-transport failures while collecting `POST /ai/chat` and the follow-up search used for retrieval context. Those cases MUST SKIP with a reason that names timeout or transport failure. Remaining goldens MUST still be attempted. The collection HTTP timeout MUST be at least 300 seconds by default (an operator override MAY be documented). The CLI MAY retry a timed-out chat once. An uncaught transport exception MUST NOT abort the process. Zero scored rows after SKIPs MUST still exit non-zero without fabricating aggregates.

#### Scenario: Chat read timeout is SKIP
- **GIVEN** a golden whose `POST /ai/chat` exceeds the collection HTTP timeout
- **WHEN** the quality CLI collects that case
- **THEN** the case is SKIPPED with a reason that names timeout
- **AND** the process does not print an uncaught timeout traceback as the run result

#### Scenario: Remaining cases still run after a timeout
- **GIVEN** a 12-case live quality run
- **AND** the first chat collection times out
- **WHEN** the CLI continues
- **THEN** later cases are still attempted
- **AND** the timeout appears in the SKIP list

#### Scenario: All timeouts fail closed
- **GIVEN** every case SKIPs because of timeout or other collection failure
- **WHEN** the quality CLI finishes
- **THEN** the process exits non-zero
- **AND** it does not print fabricated successful aggregate means
