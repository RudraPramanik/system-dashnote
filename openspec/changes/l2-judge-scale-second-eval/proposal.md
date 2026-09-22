## Why

The first local L2 run (`evals/eval_report.md`) missed the 0.7 correctness and completeness floors, but the printed scores sit only on `0.00` / `0.05` / `0.10`. Collection succeeded (`n=12`, `SKIP=0`, five contexts per case). DeepEval GEval (3.9.9) asks for an integer from 0 to 10 and divides by 10, while `evals/run_quality.py` tells the judge to score from 0 to 1. A second run of the same steps would repeat the artifact. The console paste is also unusable: the Rich progress bar overwrote case lines, and reasons are printed only when a score is missing.

## What Changes

- Stop instructing the L2 judge to score on 0–1. Leave DeepEval’s default 0–10 integer scale in charge so normalized means are comparable to the 0.7 floors.
- Persist every scored case (scores and reasons) to a JSONL, and write `evals/eval_report_2.md` from that file so a console paste cannot be the only record.
- Align the style rubric with the existing chat generation contract: concise, no invented facts, marker tokens preserved, the product refusal sentence when context is thin. Style judges the answer string. Citations stay a sibling field and are not required inside the answer prose.
- Re-run the same twelve `rag_answers.jsonl` cases against local Compose and record the new aggregates honestly (README row plus `evals/article.md`).
- Do not change `RAG_SYSTEM_INSTRUCTION`, retrieval, or `/ai/agent` in this change. Generator prompt work waits until reasons from this run say the answers are wrong.

## Capabilities

### New Capabilities

### Modified Capabilities

- `ai-eval-harness`: L2 GEval must use the library 0–10 scale, must persist per-case scores and reasons, must judge style against the declared answer voice (not inline citations), and must record a second honest run that is distinct from the scale-collapsed first report.

## Impact

- Laptop-only CLI: `evals/run_quality.py`, `evals/quality_lab.py`, and tests under `tests/evals/`. No API, worker, Compose, or VPS runtime dependency.
- Operator docs: `evals/README.md`, `evals/BLUEPRINT.md` (style rubric + report path), new `evals/article.md`, new `evals/eval_report_2.md` and a scores JSONL written by the CLI.
- Tenancy unchanged: collection still uses JWT `wid` only. Soft vs hard unchanged: L2 stays off `/health`, off PR CI, and off `/ai/chat` and `/ai/agent`.
- Non-goals: no RAG prompt rewrite, no agent-answer goldens, no faithfulness metric, no collapsing chat and agent, no bypass of vector wrappers, no change to the 0.7 floors or the golden corpus.
