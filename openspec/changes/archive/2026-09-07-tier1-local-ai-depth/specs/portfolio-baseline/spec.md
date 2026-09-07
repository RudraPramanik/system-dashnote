## ADDED Requirements

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
