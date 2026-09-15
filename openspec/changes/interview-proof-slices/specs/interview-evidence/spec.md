## Purpose

Portfolio interview evidence pack: EXPERIMENTS measure→improve loops, filled local cost samples, Eval Paradox talk-track packaging, and a light messy-data demo fixture so hire conversations have showable proof without new product platforms.

## ADDED Requirements

### Requirement: EXPERIMENTS measure-improve record exists
The repository MUST include an EXPERIMENTS document (`docs/EXPERIMENTS.md` or `evals/EXPERIMENTS.md`) that records at least one complete measure→change→re-measure loop tied to the golden eval harness or a documented RAG/agent failure mode. Each loop MUST state baseline signal, change made, after signal, environment label (e.g. local/fixture), and date.

#### Scenario: Operator finds a reduce-error loop
- **GIVEN** this change is complete
- **WHEN** a reader opens the EXPERIMENTS document
- **THEN** they find at least one experiment with baseline and after measurements
- **AND** the measurements reference `PASS: X/Y` from the eval runner and/or an explicit failure mode that was fixed
- **AND** the environment is labeled (fixture, live-local, or similar) rather than claimed as a production SLO

### Requirement: Cost sample and optimization note are recorded
Operators MUST record a fixed local cost/latency sample (from Langfuse export or an equivalent scripted token/latency capture) and at least one optimization comparison (before vs after tokens-per-query, cost-per-query, or latency) in portfolio docs. Values MUST be labeled local/sample.

#### Scenario: README cost field is filled from a sample
- **GIVEN** a completed local sample run of a fixed query set
- **WHEN** portfolio quality/cost signals are updated
- **THEN** the cost/latency field contains numeric or tabular local/sample values (not only “pending”)
- **AND** an optimization note states what changed and how the sample metric moved

### Requirement: Interview talk track names the Eval Paradox
`docs/interview-talk-track.md` MUST name the Eval Paradox in interviewer-facing language and MUST point to the fixture-vs-live eval split plus the EXPERIMENTS record as the resolution strategy.

#### Scenario: Candidate can answer Eval Paradox from talk track
- **GIVEN** this change is complete
- **WHEN** a candidate reviews the interview talk track
- **THEN** they find an explicit Eval Paradox framing
- **AND** the framing references deterministic fixture CI vs live/operator evals
- **AND** it links or points to the EXPERIMENTS document

### Requirement: Messy-data demo artifact is discoverable
The repository MUST include a light messy-data demonstration artifact: at least one edge-case file fixture (ugly, unsupported, empty-extract, or parse-failure path) and a short pipeline diagram in docs that maps upload → parse → extract → index → retrieve. The artifact MUST NOT claim OCR or full enterprise ETL coverage.

#### Scenario: Interviewer can see the messy-data story
- **GIVEN** this change is complete
- **WHEN** a reader follows portfolio or AI docs links for messy data
- **THEN** they can locate the edge-case fixture description or path
- **AND** they can locate a pipeline diagram covering parse through retrieval
- **AND** documentation does not claim scanned-PDF OCR as shipped
