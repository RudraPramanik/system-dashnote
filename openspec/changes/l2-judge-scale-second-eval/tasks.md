## 1. Judge contract

- [x] 1.1 In `evals/run_quality.py`, remove the “score from 0 to 1” step from correctness, completeness, and style. Do not pass a custom `rubric` into `GEval`.
- [x] 1.2 In `evals/quality_lab.py`, replace `STYLE_RUBRIC` with the declared voice (concise, no invented facts, preserve marker tokens, product refusal sentence). Keep style evaluation params on the answer string only. Do not edit `src/ai/prompts/rag.py` or `src/ai/workflows/workspace_assistant.py`.

## 2. Durable record

- [x] 2.1 At the start of a quality run, replace `evals/quality_scores.jsonl`. Append one object per scored case with `id`, `scores`, and `reasons`, including reasons when scores are numeric.
- [x] 2.2 After scoring, render `evals/eval_report_2.md` from that JSONL (environment, judge model, aggregates, `n`, SKIP reasons, per-case scores and reasons). Leave `evals/eval_report.md` unchanged.
- [x] 2.3 Print each metric reason on the console as well as storing it. The JSONL remains the source of truth if the terminal redraws.

## 3. Offline tests

- [x] 3.1 Extend `tests/evals/test_quality_lab.py` so evaluation steps do not instruct a 0–1 score, `STYLE_RUBRIC` matches the declared voice and does not require citation prose in the answer, and a fixture row list writes JSONL plus a markdown report whose aggregates match `aggregate_metric_scores`.
- [x] 3.2 Run `python -m pytest tests/evals/test_quality_lab.py -q`. No test may call NIM, Gemini, or `POST /ai/chat`.

## 4. Operator docs

- [x] 4.1 Update `evals/README.md` and `evals/BLUEPRINT.md` with the 0–10 judge scale, the JSONL and `eval_report_2.md` paths, the declared style voice, and that generator-prompt and agent-answer work stay later.

## 5. Second live run

- [x] 5.1 Run `evals/run_quality.py` against local Compose on the existing twelve `rag_answers.jsonl` cases (`--seed-live`, same JWT `wid` collection). Do not change floors or goldens to force a pass.
- [x] 5.2 Write `evals/article.md` from `evals/quality_scores.jsonl` and `evals/eval_report_2.md`: run-1 scale artifact, declared voice, run-2 numbers, deferred prompt / agent / faithfulness work. If the run fails closed, record that and do not invent means.
- [x] 5.3 Record the run’s aggregates, `n`, SKIPs, judge model, and environment in `evals/README.md`. Do not cite `evals/eval_report.md` as this change’s result.
