## ADDED Requirements

### Requirement: Langfuse dataset and sampled faithfulness judge exist as operator/nightly thickeners
The eval program MUST provide an operator-runnable Langfuse-native path: a dataset seeded from the golden corpus (or an equivalent documented subset) and a sampled faithfulness LLM-as-judge that writes scores onto traces or experiment items. This path MUST run off the `/ai/chat` and `/ai/agent` request hot path (async or batch). It MUST NOT be required to green PR CI. Fixture `evals/run_eval.py --mode fixture` MUST remain the blocking eval gate and MUST still complete without paid live LLM keys.

#### Scenario: Operator can run the judge path without changing CI
- **GIVEN** Langfuse keys are configured for the operator environment
- **WHEN** the operator runs the documented dataset/experiment or sampled-judge procedure
- **THEN** faithfulness scores are recorded in Langfuse
- **AND** GitHub Actions PR CI still runs only fixture evals and does not call the judge

#### Scenario: Hot path does not wait on a judge
- **GIVEN** a production `/ai/chat` or `/ai/agent` request
- **WHEN** the request returns an answer or `approval_required`
- **THEN** response latency MUST NOT include an LLM-as-judge completion for that turn

### Requirement: EXPERIMENTS records a judge or tracing baseline without replacing goldens
`docs/EXPERIMENTS.md` MUST include at least one dated measure→change→re-measure loop that cites either a Langfuse judge/trace signal or the golden `PASS: X/Y` harness. The loop MUST label environment (fixture / local / lab) and MUST NOT present local samples as production SLOs. The golden JSONL harness remains the C-gate.

#### Scenario: New loop is honest about environment
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/EXPERIMENTS.md`
- **THEN** they find a loop that names the environment
- **AND** they can still run `evals/run_eval.py --mode fixture` as the regression gate

## MODIFIED Requirements

### Requirement: Post-C-gate eval thickeners are documented without replacing the harness
Planning documentation for the eval program (at minimum `docs/documentation/blueprint8.md`, and `evals/README.md` when the harness exists) MUST describe post-C-gate thickeners: Langfuse-native datasets/experiments as the preferred judge/experiment path, optional recall@k or MRR on goldens, optional faithfulness/answer-relevancy as operator/nightly, and an EXPERIMENTS / before-after record that exists as a concrete in-repo file. These thickeners MUST NOT replace the golden JSONL + `run_eval.py` C-gate harness, and MUST NOT require live LLM judges to green PR CI. `evals/README.md` MUST link to the EXPERIMENTS document. After this change the Langfuse dataset + sampled faithfulness judge MUST be described as an existing operator/nightly procedure (not only a future preference).

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

#### Scenario: EXPERIMENTS is linked from evals README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find a link or pointer to the EXPERIMENTS before-after record

#### Scenario: Operator README names the runnable judge procedure
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find how to run the Langfuse dataset/faithfulness operator path
- **AND** they are told PR CI does not require that path
