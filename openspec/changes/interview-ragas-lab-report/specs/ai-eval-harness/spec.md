## ADDED Requirements

### Requirement: Live RAGAS lab surfaces actionable collection failures
When the operator RAGAS lab runs against a live API and cannot collect a scored row for a selected golden, the CLI MUST identify the case id and a concrete failure class at least as specific as: chat non-200, empty retrieval / missing context texts, empty answer, or missing judge credential (process-level). When zero rows are collected, the process MUST exit non-zero and MUST NOT print fabricated aggregate faithfulness or context-precision scores.

#### Scenario: All chat errors yield no fake scores
- **GIVEN** every selected golden returns a non-200 response from `POST /ai/chat`
- **WHEN** the operator runs the live RAGAS lab
- **THEN** each skipped case is identified with a chat failure indication
- **AND** the process exits non-zero
- **AND** aggregate faithfulness / context precision scores are not printed as successful lab results

#### Scenario: Missing judge key fails before product key fallback
- **GIVEN** the dedicated judge credential is unset or blank
- **WHEN** the operator runs the live RAGAS lab
- **THEN** the process exits non-zero naming the required judge env var
- **AND** it MUST NOT fall back to the embeddings / chat-fallback Gemini key

### Requirement: Dated RAGAS lab evidence is recorded after apply
After this change, operators MUST update `docs/EXPERIMENTS.md` with a dated RAGAS lab entry (or an update to the existing RAGAS experiment) that records either (a) collected `n`, faithfulness, context precision, judge model, SKIP notes, and environment `lab` / `live-local`, or (b) an honest blocked-collection note naming the product/API failure mode. Scores MUST NOT be labeled as production SLOs. The shareable RAGAS lab report (interview-evidence) MUST stay consistent with that EXPERIMENTS entry.

#### Scenario: EXPERIMENTS matches the shareable report
- **GIVEN** this change is complete and a lab attempt has been recorded
- **WHEN** an operator compares `docs/EXPERIMENTS.md` to the RAGAS lab report
- **THEN** both describe the same dated outcome (scores with `n`, or blocked collection)
- **AND** neither presents the outcome as a production SLO

### Requirement: Live lab preflight guidance is documented
Operator documentation for the RAGAS lab MUST state prerequisites for a meaningful live run: local API reachable, valid JWT for a workspace with seeded retrieval content (or documented seed steps), dedicated judge credential set, and RAGAS extra installed. Documentation MUST tell operators to resolve chat/search collection failures before treating missing scores as a judge-stack problem.

#### Scenario: Operator distinguishes stack failure from judge failure
- **GIVEN** this change is complete
- **WHEN** an operator reads the RAGAS lab setup / README guidance
- **THEN** they find prerequisites for live collection
- **AND** they are told that chat HTTP errors or empty retrieval are collection blockers, not RAGAS pin failures
