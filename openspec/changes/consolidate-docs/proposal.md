## Why

Human docs under `docs/` have grown into overlapping trees: two observability guides, a day-by-day ship-plan plus blueprint8 plus goal tracker, historical Composer slice prompts that already shipped, and scratch files. Readers and agents follow duplicate or dead links (`src/docs/`, `observability.md` vs `observe.md`) instead of the live contract. Reduce the tree now so the remaining files stay the current sources of truth.

## What Changes

- Publish a **small keep-set** as the operator map: README Documentation section lists only surviving files.
- **Merge** unique runbook content from `docs/observability.md` into `docs/documentation/observe.md` (single observability path). Keep `observe.md` so the in-progress `production-ai-observability` change still has a stable target.
- **Merge** still-true LLM fallback / NIM notes from `docs/nvidia.md` and `docs/documentation/issue_solve.md` into `docs/documentation/ai.md`; delete the standalone files.
- **Fold** `docs/uml/README.md` into `docs/uml/diagrams.md` and drop the dead `src/docs/lld.md` pointer.
- **Lift** any still-open unique checkboxes from `docs/ship-plan.md` into `docs/documentation/blueprint/goal.md`, then delete `ship-plan.md`.
- **Delete** historical implementation prompts and scratch: `docs/documentation/blueprint/slice1.md`–`slice7.md`, `slice7-llm-hardening.md`, `total.md`, `observation-blueprint.md`, `slice-platform.md`, `slice8_X.md`, `slice8_ci.md`, `slice8_eval.md`, `slice8_hitl.md`, `new.md`, and root `n.md`.
- **Rewrite** in-repo links (canonical docs, README, `openspec/config.yaml`) so they only point at surviving paths.
- **Keep** unique current docs: architecture (`system.md`, `ai.md`, `lld.md`, `auth.md`, `rules.md`, `frontendguide.md`), ops (`production.md`, `deploy-low.md`, `runbook.md`, `storage.md`, `devops-progress.md`, `inbound-channels.md`), portfolio (`blueprint8.md`, `goal.md`, `EXPERIMENTS.md`, interview talk track + evidence guide, `qs.md`/`qs2.md`/`qs3.md`), plus `user.md` and `smoke-conversation-titles.md`.
- **Non-goals:** application code, OpenSpec archives, sibling `dashnotes` docs, deleting `evals/README.md` or test fixture READMEs.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `canonical-docs`: Related-doc tables MUST use a single observability path (`observe.md`) and MUST NOT list deleted files or `src/docs/` locations.
- `blueprint8-ship-path`: Ship path is `blueprint8.md` + `goal.md`. MUST NOT require `ship-plan.md` or historical Composer files under `blueprint/slice*.md`.
- `portfolio-baseline`: Hiring-path lock MUST live on `blueprint8.md` / `goal.md`, not `ship-plan.md`. README Documentation links MUST resolve to surviving files only.
- `slice8x-path-blueprint`: Stop requiring `slice8_X.md` as a live Composer blueprint; operators follow `blueprint8.md` and shipped artifacts instead.
- `slice8x-path-toc`: Stop requiring `slice8_X.md` as a TOC that must exist and link to `slice8_ci.md` / `slice8_eval.md` / `slice8_hitl.md`.
- `slice8x-ci-blueprint`: Stop requiring `slice8_ci.md`; thin CI operator truth is the workflow plus `production.md` / evals docs as linked from blueprint8.
- `slice8x-eval-blueprint`: Stop requiring `slice8_eval.md`; eval operator truth is `evals/README.md` (and EXPERIMENTS).
- `slice8x-hitl-blueprint`: Stop requiring `slice8_hitl.md`; HITL operator truth is `frontendguide.md` plus live AI docs.

## Impact

- **Docs / OpenSpec context only** — no FastAPI, worker, schema, Nginx, or Compose behavior changes.
- Touched files (planned): keep-set markdown under `docs/` and `readme.md`; `openspec/config.yaml` canonical-docs list; main specs listed above (via this change’s deltas).
- **BREAKING for readers:** deleted paths 404. All in-repo markdown links to removed files MUST be rewritten in the same change.
- In-flight `production-ai-observability` continues to update `docs/documentation/observe.md` (not `docs/observability.md`).
- Tenancy / chat≠agent / soft-vs-hard health: unchanged; this change must not rewrite those laws except to drop pointers at deleted files.
