## ADDED Requirements

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
