## Why

Backend AI slices 0–7.5 and early platform work (7P.0–7P.3) are done, but the job-search path is split across `goal.md`, `production.md`, `slice-platform.md`, and explore decisions (CI → evals → HITL → prod). Without one executable blueprint, work order drifts and gates get skipped or over-blocked. We need a single Cursor-ready guideline with substages, prompts, fallbacks, and boundaries so implementation stays coherent.

## What Changes

- Author `docs/documentation/blueprint/slice8_X.md` as the Slice 8X blueprint: CI (7P.7) → evaluation harness → HITL on `/ai/agent*` (API-first) → remaining prod (7P.4–7P.6, 7P.8) → frontend deferred after that path.
- Document substages, architecture laws to paste into Composer, per-step Cursor prompts, validation gates, fallback boundaries (what not to build), and how this amends the strict “no features before 7P.8” rule for harness hardening only.
- Cross-link from related docs (`goal.md`, `production.md`, `total.md`, `slice-platform.md`) so the path is discoverable — without rewriting completed slice blueprints.
- **No application code** in this change: blueprint/docs only. Runtime CI, evals, HITL, and CD land in later apply/implement changes driven by this blueprint.

## Capabilities

### New Capabilities
- `slice8x-path-blueprint`: Requirements for the Slice 8X planning blueprint — ordered phases, substages, gates, fallbacks, Composer laws/prompts, and doc cross-links that define the CI → evals → HITL → prod path.

### Modified Capabilities
- (none in this change — runtime requirements in `production-platform`, `ai-eval-harness`, `portfolio-baseline`, and `frontend-developer-guide` stay as-is; Slice 8X only sequences how/when to implement them and documents the intentional pre-7P.8 harness exception)

## Impact

- **Docs:** `docs/documentation/blueprint/slice8_X.md` (primary); light updates to `goal.md`, `production.md`, `total.md`, and/or `slice-platform.md` for pointers and gate exception language.
- **Existing specs (downstream, not edited here):** `production-platform` (7P.7–7P.8), `ai-eval-harness` (C-gate), later HITL/agent deltas in a follow-on change.
- **Code / APIs:** none in this change.
- **Later work unlocked:** implementers follow 8X substages for `.github/workflows/ci.yml`, `evals/`, HITL interrupt/resume on agent routes, then finish 7P.4–7P.8.
- **Constraint:** Must preserve local `docker compose` and existing Slice 6 chat≠agent coexistence laws when describing future build steps.
