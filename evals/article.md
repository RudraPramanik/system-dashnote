# What the second L2 run actually measured

The first lab paste in `evals/eval_report.md` missed the 0.7 floors (correctness 0.0775, completeness 0.0833, style 0.0483). Collection had already succeeded: `n=12`, `SKIP=0`, five contexts on every case. The printed scores sat only on `0.00`, `0.05`, and `0.10`.

DeepEval GEval 3.9.9 asks for an integer from 0 to 10 and divides by 10. The evaluation steps told the judge to score from 0 to 1. `gpt-oss-20b` followed the steps. A 1 became 0.1. That paste is kept as the historical record. It is not the result of this change.

## Declared answer voice

Chat generation was not edited. `RAG_SYSTEM_INSTRUCTION` still says: use only the context, one clear sentence, markdown, chunk ids in `cited_chunk_ids`, and this refusal when context is thin:

> I could not find relevant information in your notes and files for this query.

Citations stay a sibling field on the chat response. They are grounded against retrieved chunk ids in `src/ai/services/rag_service.py`. Style now scores the answer string against that voice: concise, no invented facts, marker tokens preserved, that refusal sentence as the only non-answer. It does not require citation prose inside the answer.

The agent prompt was not changed. This run called `POST /ai/chat` only.

## Run 2

Same twelve `rag_answers.jsonl` cases, local Compose, `--seed-live`, environment `lab`, judge `nvidia_nim/openai/gpt-oss-20b`. Numbers are from `evals/quality_scores.jsonl` via `evals/eval_report_2.md`.

| | Run 1 (0–1 steps) | Run 2 (library 0–10) |
|---|---|---|
| n / SKIP | 12 / 0 | 12 / 0 |
| correctness | 0.0775 | 0.9000 |
| completeness | 0.0833 | 0.7417 |
| style | 0.0483 | 1.0000 |
| floors 0.7 | missed | met |

The jump is the scale fix plus a style rubric that matches the answer we already emit. It is not a generator-prompt improvement.

## What the reasons still say

Correctness is high because the marker tokens are in the answers. Completeness is the metric that still moves:

- `rag-ans-03-gamma-infra` correctness 0.0 and completeness 0.5: the answer was the marker alone, without Redis or queues.
- `rag-ans-01` and `rag-ans-06` completeness 0.5: marker present, linking phrase (alpha delivery, ARQ workers) missing.
- `rag-ans-10` completeness 0.6: Redis and queue named, `GAMMA_MARKER_44DE` omitted.
- `rag-ans-11` completeness 0.0: the judge treated markdown bold around `DELTA_MARKER_A1B2` as not exact. Style still scored that answer 1.0.

Those are answer-shape gaps. They are the next loop, after reading reasons, not a reason to retune the floor.

## Deferred

- Generator prompt edits, including whether bold markers should be plain text.
- Agent-answer goldens.
- A faithfulness metric against retrieval context.
- Treating L2 means as a production SLO or a PR gate.

Each scored run replaces `evals/quality_scores.jsonl` and rewrites `evals/eval_report_2.md` from it. The console is not the record: DeepEval’s progress bar redraws lines, and a Windows console encoding error can drop a character from a printed reason. The JSONL keeps the full text.
