## ADDED Requirements

### Requirement: Eval lifecycle blueprint is the map for post-C-gate answer quality
The eval program MUST treat `evals/BLUEPRINT.md` as the canonical map for answer-quality evaluation after the C-gate. `evals/README.md` MUST link to that blueprint. The golden JSONL + `evals/run_eval.py` fixture harness MUST remain the blocking PR eval gate. LLM-as-judge answer metrics (correctness, completeness, style) MUST be documented as a local / pre-deploy / nightly suite, not as a replacement for fixture CI, and MUST NOT be required to green PR CI.

#### Scenario: Operator sees C-gate and quality suite as distinct
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find how to run `evals/run_eval.py --mode fixture`
- **AND** they find a pointer to `evals/BLUEPRINT.md` for the answer-quality lifecycle
- **AND** they are told PR CI does not run the LLM-as-judge quality suite

### Requirement: Existing operator labs remain until a later change supersedes them
Until a follow-on change explicitly folds or retires them, the Langfuse dataset / sampled faithfulness procedure and the RAGAS lab MUST remain documented as existing operator/nightly paths. The lifecycle blueprint MAY mark them as thickeners or as candidates to fold into the DeepEval suite later. This change MUST NOT delete those runners or require RAGAS scores to claim C-gate.

#### Scenario: RAGAS and Langfuse paths are still discoverable
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they can still find the Langfuse faithfulness operator path
- **AND** they can still find the RAGAS lab setup and command
- **AND** those paths are not presented as production SLOs or PR merge gates
