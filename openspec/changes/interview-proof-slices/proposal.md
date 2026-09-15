## Why

Interview / portfolio questions on cost control, eval-driven error reduction, messy enterprise data, and the Eval Paradox need *showable proof*, not architecture talk alone. The product already has Langfuse token/cost fields, a golden eval harness, a file parse→index pipeline, and a fixture-vs-live eval split — but D4 cost/latency is still pending, there is no EXPERIMENTS before/after record, the talk track does not name the Eval Paradox, and messy-data “horror story” fixtures are thin.

## What Changes

- Fill the README (D4) **cost / latency** table from a fixed local sample run (Langfuse export or scripted tokens), labeled **local/sample** — not a production SLO.
- Record **one optimization run** (smallest ROI win: e.g. tighter char budget, structured token caps already in place, or embedding-cache hit narrative with measured $/query or tokens/query before vs after).
- Add `docs/EXPERIMENTS.md` (or equivalent under `evals/`) with **≥1 measure→improve loop**: baseline `PASS: X/Y` or failure mode → change → re-measure → outcome (the “reduced error rate” story).
- Extend `docs/interview-talk-track.md` to **name the Eval Paradox** and point at fixture CI vs live/operator evals + EXPERIMENTS.
- Optional light messy-data slice: **one ugly/unsupported or edge PDF (or parse-failure) fixture** plus a short pipeline diagram in docs so enterprise “messy data shock” is demonstrable without OCR/product expansion.
- Update `goal.md` / portfolio trackers so D4 and EXPERIMENTS status reflect reality after the runs.

**Non-goals:** No `ai_usage` metering API, no RAGAS/faithfulness CI gate, no OCR pipeline, no hybrid search/reranker, no production SLO claims from local samples.

## Capabilities

### New Capabilities

- `interview-evidence`: Lightweight portfolio evidence pack — EXPERIMENTS measure→improve record, cost-sample procedure outcomes, Eval Paradox talk-track packaging, and optional messy-data demo fixture/diagram discoverability.

### Modified Capabilities

- `portfolio-baseline`: Cost/latency field moves from pending placeholder to filled **local/sample** values with an optimization note; talk track / linked docs must surface Eval Paradox and EXPERIMENTS; honest labeling preserved.
- `ai-eval-harness`: Post-C-gate EXPERIMENTS / before-after record becomes a concrete in-repo artifact (not only mentioned in blueprint), with at least one reduce-error or quality loop tied to the golden harness.

## Impact

- Docs: `readme.md`, `evals/README.md`, `docs/interview-talk-track.md`, new `docs/EXPERIMENTS.md` (or `evals/EXPERIMENTS.md`), possibly `docs/documentation/blueprint/goal.md`, optional messy-data diagram under `docs/documentation/`.
- Ops evidence: one local Langfuse (or scripted) cost sample; one eval baseline→fix→re-run (may add 1–2 golden cases / fixtures if a real failure is used).
- Optional: fixture file under `evals/fixtures/` or `tests/` for parse/edge PDF — no API contract change required.
- No breaking API changes; no new runtime dependencies required for the doc/evidence path. Langfuse keys needed only for the cost sample if using live traces.
