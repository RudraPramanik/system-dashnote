## 1. Author blueprint8.md

- [x] 1.1 Write `docs/documentation/blueprint8.md` with purpose, “follow this first,” and links to `blueprint/slice8_X.md`, `slice8_ci.md`, `slice8_eval.md`, `slice8_hitl.md`, `frontendguide.md`, `goal.md`, and `production.md`
- [x] 1.2 Document Alive law (API + FE + AI remain shippable; VPS vs local/nightly/fixture split; chat≠agent coexistence)
- [x] 1.3 Document Tier 0 job gate (A/B/C/D aligned with `goal.md`) and that GraphRAG is not required for hire-ready
- [x] 1.4 Document Tier 1 deepeners (HITL, Langfuse retrieval-depth + datasets/experiments, cost/latency, fixture CI, agent goldens, failure-mode notes) with Langfuse-native as preferred eval thickener
- [x] 1.5 Document Tier 2 lab thickeners (recall@k/MRR, faithfulness/relevancy nightly, EXPERIMENTS.md, optional hybrid/rerank) as non-PR-blocking
- [x] 1.6 Add Eval → Improve → Gate loop section plus short GraphRAG introduction with explicit deferral / non-productization
- [x] 1.7 Add explicit non-goals (Neo4j on VPS, multi-agent supervisor, live LLM judges in PR CI, DeepEval-required path)

## 2. Lock ship-plan.md

- [x] 2.1 Add a top “Locked path” callout in `docs/ship-plan.md` pointing to `docs/documentation/blueprint8.md`
- [x] 2.2 Align Phase 1 / Phase 2 checklists with blueprint8 Tier 0 then Tier 1/2 (HITL, Langfuse depth, experiments, optional recall/faithfulness)
- [x] 2.3 Lightly correct Day-0 gap table where clearly stale (e.g. CI/workflows already present) and point to `production.md` for 7P truth without full day-number rewrite

## 3. Cross-link blueprint/ consistency

- [x] 3.1 Update `docs/documentation/blueprint/goal.md` to point operators to blueprint8 as default, keeping Slice 8X detail links
- [x] 3.2 Update `docs/documentation/production.md` with a short blueprint8 pointer (default path) while preserving 7P status truth
- [x] 3.3 Update `docs/documentation/blueprint/total.md` and `docs/documentation/blueprint/slice8_X.md` so Slice 8X is labeled detail/index under blueprint8 leadership
- [x] 3.4 Add a one-line pointer in `docs/documentation/blueprint/slice-platform.md` if it currently only references Slice 8X without blueprint8

## 4. Verify docs-only gate

- [x] 4.1 Confirm no application code, API, dependency, or eval harness implementation changes landed in this apply
- [x] 4.2 Spot-check that blueprint8, ship-plan, and tracker pointers do not contradict deploy-first compatibility or require GraphRAG for the job gate
