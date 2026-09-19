## ADDED Requirements

### Requirement: L3 observability stays off the C-gate and hot-path judge
The eval program MUST treat Langfuse traces, Prometheus quality counters, and `POST /ai/feedback` as L3 serving observability. PR CI MUST remain `evals/run_eval.py --mode fixture` and MUST NOT require Langfuse keys, feedback calls, or an LLM-as-judge. `/ai/chat` and `/ai/agent` MUST return without awaiting GEval, RAGAS, or a Langfuse faithfulness job. L3 MUST NOT replace L0/L1 `PASS: X/Y` or L2 quality aggregates.

#### Scenario: Fixture CI stays keyless
- **GIVEN** this change is complete
- **WHEN** an operator inspects `.github/workflows/ci.yml`
- **THEN** the blocking eval step is fixture mode only
- **AND** the workflow does not invoke Langfuse seed, feedback, or `run_quality.py`

#### Scenario: Serving does not wait on a judge
- **GIVEN** a production `/ai/chat` or `/ai/agent` request
- **WHEN** the request returns an answer or `approval_required`
- **THEN** response latency MUST NOT include an LLM-as-judge completion for that turn

### Requirement: L3 apply re-validates L0/L1 alignment
This change’s apply MUST re-run `evals/run_eval.py --mode fixture` and record the actual `PASS: X/Y`. Operator docs MUST still state that L0 and L1 share the same `evals/golden/` corpus and scorers, that fixtures are the recorded L1 contract, and that fixture-only / unwired live trajectories SKIP in live mode. A previous dated fixture or live row MUST NOT be reused as proof that L0/L1 alignment still holds after this change. L3 work MUST NOT change case ids or scoring rules in a way that splits the two modes into separate corpora.

#### Scenario: Fresh fixture summary is recorded during L3 apply
- **GIVEN** this change’s apply has run `evals/run_eval.py --mode fixture`
- **WHEN** an operator opens `evals/README.md`
- **THEN** the latest recorded fixture row matches that run’s `PASS: X/Y`
- **AND** the text still states L0/L1 share goldens and scorers
- **AND** the text does not claim L0/L1 alignment from an older apply only

#### Scenario: Shared scoring contract is unchanged
- **GIVEN** this change is complete
- **WHEN** an operator compares L0 fixture mode and L1 live mode
- **THEN** eligible retrieval/tenant cases still use the same markers and isolation rules
- **AND** `mode_hint` / `skip_if_modes` remain the eligibility law

### Requirement: L3 apply records an honest observability proof
Operators MUST prove L3 on a reachable stack with Langfuse keys already available to them (operator `.env` or `.env.production` — never pasted into docs). The apply MUST record that a real `/ai/chat` or `/ai/agent` turn produced a Langfuse parent observation, that `POST /ai/feedback` returned success for a JWT-owned thread, and that `/metrics` still exposes the documented low-cardinality AI quality counters. Prefer a stack already proven by L1. A previous observe.md narrative MUST NOT be reused as proof that this change works. Missing traces MUST be reported honestly (env alias, keys, or network) — not invented.

#### Scenario: Fresh L3 proof is recorded
- **GIVEN** this change’s apply has exercised a Langfuse-enabled turn and `POST /ai/feedback`
- **WHEN** an operator opens `evals/README.md`
- **THEN** the latest recorded L3 row names the date, environment, and what was proven (trace parent name, feedback HTTP outcome, metrics present)
- **AND** the text does not claim success from an older observability write-up

#### Scenario: Soft tracing failure is honest
- **GIVEN** Langfuse keys are set but no trace appears
- **WHEN** apply validation finishes
- **THEN** docs record the failure and the suspected cause (host alias, client init, or outbound)
- **AND** they do not invent a successful Langfuse row

### Requirement: Operator docs name L3 procedure and layer alignment
`evals/README.md` and `evals/BLUEPRINT.md` MUST document how to enable Langfuse (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, and the `LANGFUSE_BASE_URL` alias), confirm a `rag.answer` or `agent.turn` trace, call `POST /ai/feedback`, scrape `/metrics`, that L3 is serving observability (not a PR merge gate), L0/L1 alignment, and L2/L3 placement (GEval stays pre-deploy; traces/thumbs are not SLOs). Docs MUST use placeholders only — never live keys or JWTs.

#### Scenario: Operator can run L3 from the README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find L3 steps for traces, feedback, and Prometheus
- **AND** they find that PR CI stays fixture-only
- **AND** they find L0/L1 alignment notes and that L3 does not replace L0/L1/L2
