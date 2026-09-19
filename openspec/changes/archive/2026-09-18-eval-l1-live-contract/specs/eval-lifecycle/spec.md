## ADDED Requirements

### Requirement: Second implementation phase after L0 is L1 live contract
The lifecycle blueprint MUST name L1 (live API contract against Compose or staging) as the second implementation phase after L0 fixture-gate close-out. That phase MUST close the live runner path for retrieval/tenant goldens shared with L0, operator docs for JWT live runs, the NVIDIA NIM Gemini-429 hatch for the live stack, and an honest recorded live `PASS: X/Y`. It MUST NOT require shipping DeepEval, answer goldens, or `run_quality.py`. PR CI MUST remain L0 fixture-only. Later phases (RAG answer quality, thresholds, style work, agent quality) remain separate changes.

#### Scenario: This change does not ship the judge suite
- **GIVEN** the L1 implementation change is complete
- **WHEN** an operator inspects `evals/`
- **THEN** `evals/run_eval.py --mode live` is the implemented live contract
- **AND** a DeepEval quality runner is not required to exist
- **AND** the blueprint still lists L2 as a later phase
- **AND** PR CI still runs fixture mode only

#### Scenario: Blueprint roadmap order is L0 then L1 then L2
- **GIVEN** the lifecycle blueprint phased roadmap
- **WHEN** an implementer plans the next eval change after L0
- **THEN** L1 live contract is the named next phase
- **AND** L2 LLM-as-judge is listed after L1

### Requirement: Blueprint documents L0/L1 alignment
The lifecycle blueprint MUST state that L0 fixture mode and L1 live mode share the same golden corpus and scoring contract for eligible cases. Fixtures are the recorded responses for CI; live mode proves the same markers and isolation against a real API. Trajectory goldens MAY remain fixture-primary. The blueprint MUST NOT present L0 and L1 as unrelated corpora.

#### Scenario: Operator sees one contract two modes
- **GIVEN** the lifecycle blueprint
- **WHEN** an operator reads the L0/L1 layer descriptions
- **THEN** they are told both modes use the same goldens and scoring for eligible cases
- **AND** they are told L0 is the PR CI recorded form and L1 is the live proof
