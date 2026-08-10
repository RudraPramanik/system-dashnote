## Why

The locked Slice 8X order (CI → evals → HITL → finish prod → frontend) optimizes for AI-harness depth before a live URL. The operator now prioritizes a public production demo sooner, with evaluation harness work deferred until after VPS deploy (as the next ship milestone, not abandoned). Planning docs and OpenSpec path specs still present evals/HITL before 7P.8 as the preferred spine, which will mislead the next Composer sessions.

## What Changes

- **BREAKING (planning contract):** Adopt **deploy-first ship path** as the active Slice 8X operator order: thin CI (8X.1 / 7P.7) → finish platform (7P.4–7P.6, 7P.8) → minimum frontend (B-gate) → eval harness (8X.2) against live/prod URL → HITL API (8X.3) later.
- Update `slice8_X.md` phase overview, readiness verdict, architecture-law summary, and path-divergence section so deploy-first is the **chosen** path; keep the old CI→evals→HITL→prod order documented as the alternate “AI-depth-first” path.
- Update cross-links in `goal.md`, `production.md`, and `slice-platform.md` so “what to do next” matches deploy-first (start 8X.1.0, then 8X.4 / remaining 7P — not 8X.2 immediately after CI).
- Clarify that evals remain a **job-search gate** requirement (C1–C4) but are sequenced **after** production smoke, preferably run with `--base-url` against the live API; fixture/CI-blocking evals stay a later Phase 2 concern.
- Do **not** implement CI, VPS, frontend, evals, or HITL in this change — docs + spec deltas only. Application code remains untouched.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `slice8x-path-blueprint`: Change locked phase order and gate narrative from CI→evals→HITL→prod to deploy-first (CI→finish prod→frontend→evals→HITL); redefine pre-7P.8 exception accordingly.
- `slice8x-path-toc`: Update TOC/index requirements so visible locked order and “what may run before 7P.8” match deploy-first.

## Impact

- **Docs:** `docs/documentation/blueprint/slice8_X.md`, `goal.md`, `slice-platform.md`, `docs/documentation/production.md` (and any short pointers that hard-code CI→evals→HITL→prod as the chosen path). Platform *behavior* specs (`production-platform`) stay unchanged — only planning pointers in those docs are edited.
- **OpenSpec:** Delta specs under this change for the two modified path capabilities; main specs sync on archive/apply of deltas per project workflow.
- **Code / APIs / infra:** None in this change. Next implementation change after this lands should still start at **8X.1.0** (thin CI inventory), then finish **7P.4–7P.8**.
- **Deferred (explicit non-goals here):** Writing `.github/workflows/ci.yml`, deploy scripts, `evals/`, HITL interrupt/resume, or frontend app work.
