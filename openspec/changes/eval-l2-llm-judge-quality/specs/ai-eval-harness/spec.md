## ADDED Requirements

### Requirement: RAG answer golden corpus exists for L2
The repository MUST include `evals/golden/rag_answers.jsonl` with about 10–20 RAG answer cases for `POST /ai/chat`. Each case MUST include stable `id`, `theme` (`rag_answer`), `surface`, `query_text`, `expected_output`, and `completeness_checklist`. Cases MUST use `seed` and/or reuse retrieval-marker note content so entity IDs are not hard-coded to one environment. Initial goldens MAY be AI-drafted and MUST be labeled as such in operator docs. Agent trajectory goldens MUST NOT be treated as this answer suite.

#### Scenario: Corpus meets minimum shape
- **GIVEN** this change is complete
- **WHEN** an operator inspects `evals/golden/rag_answers.jsonl`
- **THEN** there are at least ten RAG answer cases
- **AND** each case has `id`, `query_text`, `expected_output`, and `completeness_checklist`
- **AND** cases do not hard-code environment-only `note_id` / `chunk_id` without seed or shared marker content

#### Scenario: Surface is chat not agent
- **GIVEN** the L2 answer corpus
- **WHEN** an operator reads case `surface` values
- **THEN** phase-1 cases target `POST /ai/chat`
- **AND** `/ai/agent` is not used as a substitute for chat evals in this change

### Requirement: L2 quality CLI collects chat answers and scores with an LLM judge
The repository MUST provide `evals/run_quality.py` (and a laptop-only quality requirements file) that loads the RAG answer goldens, authenticates with a JWT against a configurable base URL, calls `POST /ai/chat` with message-only scoping (JWT `wid`), collects `actual_output` and retrieval context when present, and scores with LLM-as-judge metrics for correctness, completeness, and style. Correctness and completeness MUST enforce documented hard floors. Style MUST always be reported (loose or no floor allowed at first). The runner MUST NOT import the judge library from `evals/run_eval.py`. The quality extra MUST NOT be added to API, worker, Compose serving images, or VPS as a runtime dependency.

#### Scenario: Operator runs the quality CLI
- **GIVEN** a reachable API, a valid JWT, the dedicated judge credential, and the quality extra installed on the laptop
- **WHEN** the operator runs `evals/run_quality.py` with base URL and token
- **THEN** the CLI prints environment label, judge model, per-metric aggregates, collected `n`, and SKIP count/reasons
- **AND** exit is non-zero when hard floors for correctness or completeness are missed on a scored run with `n > 0`

#### Scenario: SKIP on bad collection rows
- **GIVEN** a case whose live chat returns non-200, empty answer, or empty retrieval
- **WHEN** the quality CLI processes that case
- **THEN** the case is counted as SKIP with a reason
- **AND** it is not scored as a successful judge row

### Requirement: L2 judge fails closed and never uses the product Gemini key
The quality CLI MUST require a dedicated judge credential (`GEMINI_API_KEY_2` or the documented successor). Missing or blank judge credential MUST exit non-zero and name the env var. The CLI MUST NOT fall back to `GEMINI_API_KEY`. Zero scored rows MUST exit non-zero without fabricating aggregate scores. Required metrics that are all NaN / non-numeric MUST exit non-zero.

#### Scenario: Missing judge key fails closed
- **GIVEN** the dedicated judge credential is unset or blank
- **WHEN** the operator runs `evals/run_quality.py`
- **THEN** the process exits non-zero with a message that names the required env var
- **AND** it MUST NOT use the product embeddings / chat-fallback Gemini key

#### Scenario: Empty collection is not success
- **GIVEN** every case SKIPPED or collection yields zero scored rows
- **WHEN** the quality CLI finishes
- **THEN** the process exits non-zero
- **AND** it does not print fabricated successful aggregate means

### Requirement: L2 live collection aligns with L1 tenancy and NIM hatch
L2 answer collection MUST authenticate with the same JWT workspace contract as L1 (`wid` from token only; no workspace id from query/body for scoping). Operators MUST prefer a stack already proven by L1 live when available. If Gemini rate-limit / 429 blocks product chat, embed, or related live collection, operators MUST use NVIDIA NIM with a different free/catalog model via `LLM_MODEL` / `LLM_MODEL_FALLBACKS` and recreate `api` + `worker`, then re-run L2 — without putting an LLM-as-judge on `/ai/chat` or `/ai/agent`. Tenant-isolation C-gate goldens remain the isolation proof; L2 MUST NOT claim to replace them. PR CI MUST remain L0 fixture-only and MUST NOT invoke `run_quality.py`.

#### Scenario: Collection uses JWT workspace only
- **GIVEN** the operator runs L2 against a live base URL with a JWT
- **WHEN** the CLI posts `POST /ai/chat` for a golden query
- **THEN** workspace scoping comes from the JWT only
- **AND** forged workspace fields MUST NOT expand retrieval

#### Scenario: Gemini 429 on product stack uses NIM
- **GIVEN** product chat or embed returns rate-limit / 429 during L2 collection
- **WHEN** the operator follows eval docs
- **THEN** they switch to a different NVIDIA NIM free/catalog model via the product candidate list, recreate `api` + `worker`, and re-run
- **AND** they do not invent judge scores
- **AND** PR CI still does not require NIM or judge keys

### Requirement: L2 apply records an honest quality run
Operators MUST be able to run `evals/run_quality.py` against a reachable base URL after this change and record the actual aggregates, `n`, SKIP count/reasons, judge model, and environment (`lab` or `pre-deploy`) in `evals/README.md` (and MAY add a dated note in EXPERIMENTS). The documented numbers MUST match that run. A previous RAGAS or older row MUST NOT be reused as proof that this change works. Zero scored cases MUST NOT be documented as a successful L2 close-out.

#### Scenario: Fresh quality summary is recorded
- **GIVEN** this change’s apply has run `evals/run_quality.py` against a real stack with at least one scored case (or recorded an honest fail-closed outcome when collection/judge blocked)
- **WHEN** an operator opens `evals/README.md`
- **THEN** the latest recorded L2 row matches that run’s aggregates / `n` / SKIPs (or names the fail-closed reason)
- **AND** the text does not claim success from an older unrelated lab row

### Requirement: Operator docs name L2 procedure and L1/L2 alignment
`evals/README.md` and `evals/BLUEPRINT.md` MUST document how to install the quality extra, set the dedicated judge key, run `evals/run_quality.py`, that L2 is local/pre-deploy (not a PR merge gate), L1/L2 alignment (JWT tenancy, seed law, NIM hatch for product 429), and that RAGAS/Langfuse labs remain until a later change folds or retires them.

#### Scenario: Operator can run L2 from the README
- **GIVEN** this change is complete
- **WHEN** an operator opens `evals/README.md`
- **THEN** they find the quality CLI command with base URL and token
- **AND** they find that PR CI stays fixture-only
- **AND** they find L1/L2 alignment notes and the NVIDIA NIM hatch for Gemini 429 on the product stack during collection

#### Scenario: Blueprint marks L2 as the shipped quality phase
- **GIVEN** this change is complete
- **WHEN** an operator opens the phased roadmap in `evals/BLUEPRINT.md`
- **THEN** L2 LLM-as-judge / `run_quality.py` is listed as the phase after L1
- **AND** thresholds/baseline, generator style work, and agent answer goldens remain later phases
