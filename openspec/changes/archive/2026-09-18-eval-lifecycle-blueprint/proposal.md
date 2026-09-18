## Why

The C-gate fixture harness (`evals/run_eval.py`) and the RAGAS lab prove retrieval/tenant/trajectory and optional faithfulness, but they do not produce a production-shaped **answer-quality** program: frozen goldens with expected answers, LLM-as-judge scores (correctness / completeness / style), a single operator CLI, and a pre-deploy gate that stays off the VPS hot path. Without an end-to-end blueprint first, DeepEval work would land as another one-off script instead of a modular eval lifecycle we can follow in phases.

## What Changes

- Add a **canonical eval lifecycle blueprint** under `evals/` (single Markdown source of truth) covering enterprise/startup eval practice adapted to this repo: layers (fixture CI vs live API vs LLM-as-judge vs production observability), data contracts, DeepEval GEval metrics, gold curation, single-file terminal runner, CI vs pre-deploy vs production placement, and phased rollout (RAG answers first, agent later).
- Point `evals/README.md` (and a light EXPERIMENTS / interview pointer if needed) at that blueprint so operators do not treat RAGAS or fixture-only as the whole program.
- Lock the program in specs so later implementation changes follow the blueprint instead of inventing a parallel eval tree.
- **This change does not implement DeepEval, new goldens, or a new runner.** Those are later OpenSpec changes, one phase at a time.

## Capabilities

### New Capabilities
- `eval-lifecycle`: Production-grade eval program for DashNoteSystem — modular `evals/` layout, golden/answer datasets, DeepEval LLM-as-judge suite (correctness, completeness, style), single CLI that collects and scores to the terminal, and explicit placement (PR fixture vs pre-deploy judge vs production traces). The blueprint document is the operator-facing contract; code lands in follow-on changes.

### Modified Capabilities
- `ai-eval-harness`: The existing fixture + RAGAS + Langfuse operator paths remain. The harness MUST treat the new `evals/` lifecycle blueprint as the map for post-C-gate answer evaluation; DeepEval MUST NOT replace `run_eval.py` fixture CI; RAGAS remains an optional lab until a later change folds or retires it.

## Impact

- **Docs (this change):** New blueprint Markdown under `evals/`; README (and optional EXPERIMENTS / interview) links. No API, worker, Compose, or VPS changes.
- **Code:** None in this change. Future phases add DeepEval extras, answer goldens, and a single runner in `evals/` only — never in the API image or on `/ai/chat` / `/ai/agent` request latency.
- **Tenancy:** Unchanged. Live collection continues to use JWT `wid` only.
- **CI:** Unchanged. PR CI stays fixture-only. Judge suites stay local / pre-deploy / nightly.
- **Deps:** No new runtime dependencies in this change. Later DeepEval extras are laptop/operator-only, dedicated judge key (`GEMINI_API_KEY_2` or successor), never product Gemini.
- **Non-goals:** Do not collapse chat and agent. Do not put LLM-as-judge on the hot path. Do not make DeepEval a PR merge gate. Do not move eval data outside `evals/`. Do not rewrite slice8 Cursor prompts (`slice8_eval.md`) — that remains the C-gate implementation history.
