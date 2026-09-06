## Why

Operators currently have a strong Slice 8X / goal / ship-plan spine, but no single “alive product + job gate + top-percentile AI eng depth” document. Hiring readiness needs one authoritative path: keep API/FE/AI shippable anytime, finish the job gate, then thicken with HITL, Langfuse-depth evals, and optional local Tier-2 lab work—without orphaning existing `blueprint/` detail slices.

## What Changes

- Add `docs/documentation/blueprint8.md` as the **operator-default** ship path (job gate + Alive law + Tier 1/2 “ahead of ~97%” track).
- Lock that path into `docs/ship-plan.md` (Phase 1 / Phase 2 align to blueprint8; outdated Day-0 gaps corrected where already false).
- Keep consistency with `docs/documentation/blueprint/` detail docs (`slice8_X.md`, `slice8_eval.md`, `slice8_hitl.md`, `goal.md`, `total.md`, `production.md`) via pointers—**blueprint8 leads; detail blueprints remain executable**.
- Include a **small GraphRAG introduction** (concepts + when-not-now) inside blueprint8; do **not** productize Neo4j/GraphRAG on the VPS path.
- Document eval stack preference: **Langfuse-native** (datasets/experiments/judges) as primary thickener after C-gate; RAGAS nightly optional; DeepEval not required.
- Document VPS vs local split: 1–2GB VPS–hostile work stays local/nightly/CI fixtures only.

## Capabilities

### New Capabilities
- `blueprint8-ship-path`: Authoritative blueprint8 document, Alive law, Tier 0/1/2 map, GraphRAG intro (non-goals), and cross-links into ship-plan + existing blueprint detail docs.

### Modified Capabilities
- `slice8x-path-blueprint`: Operator default becomes blueprint8; `slice8_X.md` remains the detail index under `blueprint/` and must not contradict blueprint8’s Alive + Tier map.
- `portfolio-baseline`: Ship-plan / portfolio packaging must treat blueprint8 as the locked hiring path and keep honest live/eval/cost claims.
- `ai-eval-harness`: Extend C-gate expectations with documented Tier-2 thickeners (Langfuse retrieval payload enrichment plan, fixture CI, optional recall@k / faithfulness as nightly—not PR-blocking).

## Impact

- Docs only for this change’s apply phase: `blueprint8.md`, `ship-plan.md`, and short pointers in `blueprint/` + `goal.md` / `production.md` / `total.md` as needed.
- No application code, API, or dependency changes in this change.
- Future implementation (evals runner, HITL code, Langfuse span enrichment) remains owned by existing Slice 8X detail blueprints / later apply changes—blueprint8 sequences and scopes them.
- GraphRAG remains optional forever unless a later change authorizes product work; blueprint8 only introduces the idea.
