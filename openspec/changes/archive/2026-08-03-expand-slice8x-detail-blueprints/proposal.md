## Why

`slice8_X.md` correctly locks the CI → evals → HITL → prod order, but each phase is still a single coarse Composer prompt. That is too thin for agentic coding compared to Slice 6/7 (multi-substep laws, NEW FILES / NEVER TOUCH, per-file tasks, gates). Empty detail files `slice8_ci.md`, `slice8_eval.md`, and `slice8_hitl.md` were created for option B (split blueprints). They need Slice-6-grade substages so agents can ship clean features without boiling the ocean or breaking local compose.

## What Changes

- Author `docs/documentation/blueprint/slice8_ci.md` — multi-substep CI blueprint (inventory → workflow skeleton → pytest job green → docker build gate), with laws, fallbacks, and Cursor OBJECTIVE prompts.
- Author `docs/documentation/blueprint/slice8_eval.md` — multi-substep eval blueprint (schema → retrieval/tenant goldens → runner → agent trajectories → optional CI wire).
- Author `docs/documentation/blueprint/slice8_hitl.md` — multi-substep HITL blueprint (interrupt → SSE → resume → script/tests; FE out of scope).
- Slim `docs/documentation/blueprint/slice8_X.md` into a TOC / law / gate-exception index that points at the three detail files (and keeps 8X.4/8X.5 as pointers to platform + frontendguide).
- Light cross-link updates so `total.md` / `goal.md` / `production.md` / `slice-platform.md` discover the split files.
- **No application code** — documentation blueprints only. Runtime CI/evals/HITL remain later implement changes.

## Capabilities

### New Capabilities
- `slice8x-ci-blueprint`: Requirements for the Slice 8X CI detail blueprint (`slice8_ci.md`) — substages, laws, gates, fallbacks for thin GitHub Actions CI.
- `slice8x-eval-blueprint`: Requirements for the Slice 8X eval detail blueprint (`slice8_eval.md`) — substages for golden corpus, runner, agent trajectories, CI vs live split.
- `slice8x-hitl-blueprint`: Requirements for the Slice 8X HITL detail blueprint (`slice8_hitl.md`) — substages for interrupt, SSE approval, resume, API-first gate.
- `slice8x-path-toc`: Requirements for `slice8_X.md` as TOC/index — must link 8X.1–8X.3 to the three detail blueprints; keep order, laws, and pre-7P.8 exception; leave 8X.4/8X.5 as pointers.

### Modified Capabilities
- (none in main `openspec/specs/` — prior change’s `slice8x-path-blueprint` is not archived to main yet; TOC behavior is captured as new `slice8x-path-toc`)

## Impact

- **Docs:** `slice8_ci.md`, `slice8_eval.md`, `slice8_hitl.md` (fill); `slice8_X.md` (slim to TOC); optional pointer tweaks in related blueprint/tracker docs.
- **Prior change:** `slice8x-ci-evals-hitl-blueprint` remains the parent path; this change expands detail without redoing completed tracker cross-links unless needed.
- **Code / APIs / workflows:** none in this change.
- **Downstream:** Agents implement 8X.1 from `slice8_ci.md`, etc., one substep per session.
