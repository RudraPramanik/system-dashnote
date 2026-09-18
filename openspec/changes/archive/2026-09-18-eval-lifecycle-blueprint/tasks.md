## 1. Canonical blueprint

- [x] 1.1 Create `evals/BLUEPRINT.md` with every section listed in design.md Decision 8 (purpose through non-goals)
- [x] 1.2 Include the four-layer diagram (L0 fixture CI, L1 live contract, L2 DeepEval quality, L3 prod observability) and state PR CI vs pre-deploy vs hot-path placement
- [x] 1.3 Document target `evals/` layout and the planned single CLI `python evals/run_quality.py` as **planned**, not as a command that exists today
- [x] 1.4 Specify RAG answer golden schema, metric policy (correctness/completeness hard gates; style always reported; fail-closed `n`/SKIP/NaN), JWT `wid` tenancy, dedicated judge key, and the phase 0→5 roadmap
- [x] 1.5 State that this file is not `slice8_eval.md`; C-gate fixture harness and existing RAGAS/Langfuse labs remain until a later change supersedes them

## 2. Discoverability

- [x] 2.1 Add a Post-C-gate pointer in `evals/README.md` to `evals/BLUEPRINT.md` that distinguishes fixture CI from the planned quality suite; keep RAGAS and Langfuse sections runnable
- [x] 2.2 Add a one-line pointer from `docs/EXPERIMENTS.md` intro to the blueprint (do not duplicate the lifecycle)
- [x] 2.3 Add a one-line pointer from `docs/interview-talk-track.md` Eval Paradox paragraph to `evals/BLUEPRINT.md`

## 3. Boundary check

- [x] 3.1 Confirm this change adds no DeepEval dependency, no `run_quality.py`, no `rag_answers.jsonl`, and no CI/VPS/API-image judge wiring
- [x] 3.2 Confirm `docs/documentation/blueprint/slice8_eval.md` was not rewritten
