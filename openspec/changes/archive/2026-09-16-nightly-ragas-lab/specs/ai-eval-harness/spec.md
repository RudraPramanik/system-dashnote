## ADDED Requirements

### Requirement: Operator RAGAS lab is runnable off the product path
The eval program MUST provide an operator-runnable RAGAS (or equivalent RAG metric) lab that scores question, generated answer, and retrieved context. The lab MUST use a dedicated judge credential distinct from the embeddings / chat-fallback Gemini key. The lab MUST be invocable from documentation without installing the metric library into the API runtime image. Fixture `evals/run_eval.py --mode fixture` MUST remain the blocking eval gate and MUST still complete without the judge credential or the RAGAS extra.

#### Scenario: Operator can run the lab without changing CI
- **GIVEN** the dedicated judge credential is set in the operator environment
- **AND** the documented RAGAS extra is installed in that environment
- **WHEN** the operator runs the documented lab procedure
- **THEN** the CLI prints aggregate metric scores (at least faithfulness, and context precision or context recall)
- **AND** GitHub Actions PR CI still runs only fixture evals and does not invoke the lab

#### Scenario: Missing judge credential fails closed
- **GIVEN** the dedicated judge credential is unset or blank
- **WHEN** the operator runs the lab
- **THEN** the process exits non-zero with a message that names the required env var
- **AND** it MUST NOT fall back to the embeddings / chat-fallback Gemini key

#### Scenario: Hot path does not wait on RAGAS
- **GIVEN** a production `/ai/chat` or `/ai/agent` request
- **WHEN** the request returns an answer or `approval_required`
- **THEN** response latency MUST NOT include a RAGAS or LLM-as-judge completion for that turn

### Requirement: RAGAS lab stays off VPS and out of product config
The RAGAS lab MUST NOT be deployed on the VPS, MUST NOT be added to Docker Compose API or worker images, and MUST NOT be loaded by API Settings. The judge credential placeholder MAY appear in `.env.example` for local operators. Product Settings, Compose, deploy scripts, and documented VPS `.env` MUST NOT require that credential.

#### Scenario: VPS deploy artifacts ignore the judge key
- **GIVEN** this change is complete
- **WHEN** an operator inspects Compose, API Settings, and VPS deploy env examples
- **THEN** the dedicated judge credential is absent from those product surfaces
- **AND** the API still starts without it

#### Scenario: Example env documents the operator key only
- **GIVEN** this change is complete
- **WHEN** an operator opens `.env.example`
- **THEN** they find an empty `GEMINI_API_KEY_2` placeholder labeled as the RAGAS/judge key
- **AND** comments MUST state it is local/operator-only and MUST NOT be used for embeddings

### Requirement: Live RAGAS collection keeps JWT tenancy
When the lab collects answers or contexts from a live API, it MUST authenticate with a JWT and MUST scope retrieval to that token’s workspace (`wid`). It MUST NOT accept a workspace identifier from query or body for scoping. Tenant-isolation goldens remain the C-gate; the RAGAS lab MUST NOT claim to replace them.

#### Scenario: Live collection uses JWT workspace only
- **GIVEN** the operator runs the lab against a live base URL with a JWT
- **WHEN** the lab requests chat or search for a golden query
- **THEN** workspace scoping comes from the JWT only
- **AND** forged workspace fields MUST NOT expand retrieval

### Requirement: RAGAS scores are lab records not SLOs
Operators MUST record at least one dated RAGAS lab result in `docs/EXPERIMENTS.md` with environment labeled `lab` (or `live-local`). The record MUST NOT present those scores as production SLOs. The golden JSONL harness remains the C-gate.

#### Scenario: EXPERIMENTS has an honest RAGAS row
- **GIVEN** this change is complete
- **WHEN** an operator opens `docs/EXPERIMENTS.md`
- **THEN** they find a RAGAS (or equivalent) loop that names environment `lab` or `live-local`
- **AND** the text MUST NOT call the scores a production SLO

## MODIFIED Requirements

### Requirement: Post-C-gate eval thickeners are documented without replacing the harness
Planning documentation for the eval program (at minimum `docs/documentation/blueprint8.md`, and `evals/README.md` when the harness exists) MUST describe post-C-gate thickeners: Langfuse-native datasets/experiments as the preferred in-product judge/experiment path, optional recall@k or MRR on goldens, a runnable operator/nightly RAGAS lab (faithfulness and context metrics, dedicated judge credential, off VPS and off PR CI), and an EXPERIMENTS / before-after record. These thickeners MUST NOT replace the golden JSONL + `run_eval.py` C-gate harness, and MUST NOT require live LLM judges or RAGAS to green PR CI. `evals/README.md` MUST link to the EXPERIMENTS document. After this change the Langfuse dataset + sampled faithfulness judge MUST remain documented as an existing operator/nightly procedure, and the RAGAS lab MUST be documented as an existing local/nightly procedure (not only a future preference).

#### Scenario: Operator finds preferred eval stack
- **GIVEN** blueprint8 (and evals README when present)
- **WHEN** an operator plans quality work after C-gate
- **THEN** Langfuse-native experiments/judges are documented as the primary in-product thickener
- **AND** RAGAS is documented as a runnable local/nightly lab (not VPS, not CI)
- **AND** PR CI remains fixture/deterministic-only for blocking gates

#### Scenario: C-gate remains the hire minimum
- **GIVEN** the documented eval program
- **WHEN** an operator checks the hire-ready eval minimum
- **THEN** ≥10 retrieval/tenant cases, pass/fail CLI summary, tenant isolation automation, and honest pass-rate docs remain required
- **AND** faithfulness, RAGAS scores, or recall@k are not required to claim the C-gate

#### Scenario: EXPERIMENTS is linked from evals README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find a link or pointer to the EXPERIMENTS before-after record

#### Scenario: Operator README names the runnable judge procedures
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find how to run the Langfuse dataset/faithfulness operator path
- **AND** they find how to set up and run the RAGAS lab (extra install, dedicated judge env var, command)
- **AND** they are told PR CI and VPS deploy do not require those paths
