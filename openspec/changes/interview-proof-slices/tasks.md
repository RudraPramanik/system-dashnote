## 1. EXPERIMENTS + Eval Paradox packaging

- [x] 1.1 Create `docs/EXPERIMENTS.md` with template sections: date, environment, baseline, change, after, notes
- [x] 1.2 Choose and document ≥1 measure→improve loop (harness `PASS: X/Y` and/or golden case id); run fixture eval before/after if a case is added or fixed
- [x] 1.3 Link EXPERIMENTS from `evals/README.md` (post-C-gate / thickeners section)
- [x] 1.4 Update `docs/interview-talk-track.md` to name the Eval Paradox and point at fixture vs live + EXPERIMENTS

## 2. Cost / latency sample (D4)

- [x] 2.1 Define a fixed local query set (small N) and capture cost/latency via Langfuse export or scripted `/ai/chat` + token fields
- [x] 2.2 Record one optimization comparison per design.md preference order (cache / empty-retrieval / lab budget knob); restore any temporary knobs
- [x] 2.3 Fill README quality/cost table with local/sample values + optimization note (remove pending-only state)
- [x] 2.4 Link EXPERIMENTS (and cost sample notes if separate) from README quality/cost section

## 3. Messy-data light slice

- [x] 3.1 Add one edge-case file fixture (ugly/unsupported/empty-extract/parse-failure) under tests or evals fixtures with a one-line README note
- [x] 3.2 Add a short pipeline diagram (upload → parse → extract → index → retrieve) in docs and link it from `ai.md` or README
- [x] 3.3 Explicitly state non-claim: no OCR / full enterprise ETL in that doc section

## 4. Tracker honesty + verify

- [x] 4.1 Update `docs/documentation/blueprint/goal.md` D4 (and any related checkboxes) to match filled cost table / EXPERIMENTS reality
- [x] 4.2 Sanity-check: README does not claim production SLOs; fixture `evals/run_eval.py --mode fixture` still passes if goldens changed
- [x] 4.3 Spot-check talk track + EXPERIMENTS + README links resolve
