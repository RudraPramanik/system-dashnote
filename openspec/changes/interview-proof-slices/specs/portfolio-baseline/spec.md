## ADDED Requirements

### Requirement: Portfolio surfaces EXPERIMENTS and Eval Paradox
Root README (or clearly linked docs from README) MUST link to the EXPERIMENTS measure→improve record. Interview talk-track documentation MUST name the Eval Paradox and MUST remain consistent with honest metric labeling (local/sample vs production).

#### Scenario: README reader finds EXPERIMENTS
- **GIVEN** this change is complete
- **WHEN** a reader opens the root README quality/cost or eval section
- **THEN** they find a link or clear pointer to the EXPERIMENTS document
- **AND** cost/latency values remain labeled local/sample until production smoke justifies otherwise

#### Scenario: Talk track includes Eval Paradox
- **GIVEN** this change is complete
- **WHEN** a candidate opens `docs/interview-talk-track.md`
- **THEN** the Eval Paradox is named explicitly
- **AND** the resolution strategy mentions fixture CI vs live/operator evaluation

## MODIFIED Requirements

### Requirement: Cost and latency table accepts local sample labeling
README (or clearly linked docs) MUST include a cost/latency table filled from a Langfuse export or a fixed local sample run, including at least one optimization comparison note (before vs after). Until production smoke exists, filled values MUST be labeled as local/sample (not production SLO). The field MUST NOT remain “pending fill” after this change’s evidence tasks complete.

#### Scenario: Local sample is honest
- **GIVEN** an operator records latency/cost from a local Langfuse or scripted sample
- **WHEN** the README table is updated
- **THEN** the environment is labeled local/sample
- **AND** the project does not present those numbers as verified production SLOs

#### Scenario: Optimization comparison present
- **GIVEN** the cost/latency table has been filled for this change
- **WHEN** a reader inspects the cost signal
- **THEN** they can see a before/after or optimization note tied to the same sample methodology
- **AND** the table is no longer marked only as pending fill
