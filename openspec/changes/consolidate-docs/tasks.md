## 1. Merge unique content into keep-set

- [ ] 1.1 Fold unique operator commands/diagrams from `docs/observability.md` into `docs/documentation/observe.md`; drop the dual-guide pointer
- [ ] 1.2 Move durable LLM fallback / NIM laws from `docs/nvidia.md` and `docs/documentation/issue_solve.md` into `docs/documentation/ai.md` (settings + 410/timeout; no full incident table unless one EOL warning line)
- [ ] 1.3 Diff `docs/ship-plan.md` against `docs/documentation/blueprint/goal.md` and `blueprint8.md`; lift any still-open unique boxes into `goal.md`
- [ ] 1.4 Point `blueprint8.md` at `goal.md`, `evals/README.md`, `frontendguide.md`, and `ai.md` instead of `slice8_*.md` / `ship-plan.md`
- [ ] 1.5 Fold the UML table from `docs/uml/README.md` into `docs/uml/diagrams.md` and retarget LLD to `docs/documentation/lld.md`

## 2. Rewrite live indexes and links

- [ ] 2.1 Update README Documentation (and any quality-signal links) so every target exists and none list `ship-plan.md` or deleted slice files
- [ ] 2.2 Update related-doc tables in `system.md`, `ai.md`, `lld.md`, `observe.md` to a single observability path and surviving files only
- [ ] 2.3 Update `openspec/config.yaml` canonical-docs list (one observe path; no blueprint slice dump)
- [ ] 2.4 Rewrite keep-set pointers in `goal.md`, `production.md`, `devops-progress.md`, `interview-evidence-guide.md`, and in-flight `production-ai-observability` docs so they do not cite files about to be deleted

## 3. Delete the retire-set

- [ ] 3.1 Delete `docs/observability.md`, `docs/nvidia.md`, `docs/documentation/issue_solve.md`, `docs/ship-plan.md`, `docs/uml/README.md`, and root `n.md`
- [ ] 3.2 Delete historical blueprint prompts: `slice1.md`–`slice7.md`, `slice7-llm-hardening.md`, `total.md`, `observation-blueprint.md`, `slice-platform.md`, `slice8_X.md`, `slice8_ci.md`, `slice8_eval.md`, `slice8_hitl.md`, `new.md`

## 4. Verify no live dead links

- [ ] 4.1 Grep the repo excluding `openspec/changes/archive/` for deleted basenames (`observability.md`, `ship-plan.md`, `slice8_`, `issue_solve`, `nvidia.md`, `src/docs/`) and fix remaining live hits
- [ ] 4.2 Confirm README Documentation links, `blueprint8.md` eval/HITL pointers, and `goal.md` blueprint8 lock all resolve to existing files
