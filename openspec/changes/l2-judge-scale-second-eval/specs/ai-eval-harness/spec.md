## ADDED Requirements

### Requirement: L2 judge uses the library ten-point scale
The L2 quality CLI MUST ask the judge for an integer on the library default range of 0 to 10 and MUST normalize that integer onto 0–1 before comparing it to the correctness and completeness floors. Evaluation steps MUST NOT tell the judge to return a score from 0 to 1. The CLI MUST NOT install a custom score range that changes this normalization. Hard floors stay 0.7 for correctness and completeness. Style stays reported and MUST NOT be a hard floor.

#### Scenario: Steps do not collapse the scale
- **GIVEN** the quality CLI builds its three judge metrics
- **WHEN** an operator inspects the evaluation steps sent to the judge
- **THEN** none of those steps instruct a score from 0 to 1
- **AND** a judge integer of 10 normalizes to 1.0 and an integer of 7 normalizes to 0.7

#### Scenario: Floors still apply after normalization
- **GIVEN** a scored run with `n > 0`
- **WHEN** the mean normalized correctness or completeness is below 0.7
- **THEN** the process exits non-zero
- **AND** style below 0.7 does not by itself fail the run

### Requirement: L2 style judges the declared answer voice
Style MUST score only the chat answer string. The voice MUST be: concise; no invented facts; marker tokens from the retrieved notes preserved when the answer uses them; the product refusal sentence is the allowed non-answer when context is insufficient. Style MUST NOT require citation text inside the answer. Citations remain a sibling field of the chat response and MUST NOT be copied into the judged answer to raise the style score. This change MUST NOT alter the RAG system instruction or the agent system prompt.

#### Scenario: Citations are not required inside the answer
- **GIVEN** an answer that is concise, grounded, and preserves required marker tokens
- **AND** citations exist only on the sibling citations field
- **WHEN** style is scored
- **THEN** the absence of citation prose inside the answer is not a style failure by itself

#### Scenario: Generator prompts stay unchanged
- **GIVEN** this change is applied
- **WHEN** an operator diffs the RAG system instruction and the workspace assistant prompt
- **THEN** those prompt strings are unchanged from before this change

### Requirement: L2 persists a durable per-case record
For every scored case the quality CLI MUST write the case id, each metric score, and each metric reason to a JSONL file under `evals/`. Reasons MUST be stored when the score is numeric, not only when the score is missing. The CLI MUST write `evals/eval_report_2.md` from that JSONL, including environment, judge model, aggregates, `n`, SKIP count and reasons, and the per-case scores and reasons. The console transcript MUST NOT be the only record of the run. `evals/eval_report.md` (the first scale-collapsed paste) MUST be left in place and MUST NOT be overwritten as the proof of this change.

#### Scenario: Numeric scores keep their reasons
- **GIVEN** a case the judge scores with numeric correctness, completeness, and style
- **WHEN** the CLI finishes that case
- **THEN** the JSONL row contains all three scores and all three reasons

#### Scenario: Markdown report is rendered from the JSONL
- **GIVEN** a finished run that wrote the scores JSONL
- **WHEN** an operator opens `evals/eval_report_2.md`
- **THEN** the aggregates, `n`, and per-case scores match the JSONL
- **AND** they do not depend on a console paste

## MODIFIED Requirements

### Requirement: L2 apply records an honest quality run
Operators MUST be able to run `evals/run_quality.py` against a reachable base URL after this change and record the actual aggregates, `n`, SKIP count/reasons, judge model, and environment (`lab` or `pre-deploy`) in `evals/README.md` (and MAY add a dated note in EXPERIMENTS). The documented numbers MUST match that run. A previous RAGAS or older row MUST NOT be reused as proof that this change works. Zero scored cases MUST NOT be documented as a successful L2 close-out. The proof of this change MUST be the JSONL-backed `evals/eval_report_2.md` plus an `evals/article.md` that states the run-1 scale artifact, the declared answer voice, the run-2 numbers taken from that JSONL, and the deferred work (generator prompt edits, agent answers, faithfulness). `evals/eval_report.md` MUST NOT be cited as the successful result of this change.

#### Scenario: Fresh quality summary is recorded
- **GIVEN** this change’s apply has run `evals/run_quality.py` against a real stack with at least one scored case (or recorded an honest fail-closed outcome when collection/judge blocked)
- **WHEN** an operator opens `evals/README.md`
- **THEN** the latest recorded L2 row matches that run’s aggregates / `n` / SKIPs (or names the fail-closed reason)
- **AND** the text does not claim success from an older unrelated lab row

#### Scenario: Article matches the second run
- **GIVEN** the scores JSONL and `evals/eval_report_2.md` from this change’s run
- **WHEN** an operator opens `evals/article.md`
- **THEN** the numbers in the article match that JSONL
- **AND** the article names the 0–1 step versus 0–10 library scale as the run-1 failure mode
- **AND** the article does not claim a generator-prompt improvement from this change
