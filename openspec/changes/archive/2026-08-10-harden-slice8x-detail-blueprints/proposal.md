## Why

A review of `slice8_ci.md`, `slice8_eval.md`, and `slice8_hitl.md` found real implementability gaps (eval fixture/seed contracts, HITL resume tenancy + SSE lifecycle, CI env/apt inventory depth) and one false “fix” (force Python 3.11) that would break Dockerfile alignment. The detail blueprints need hardening from grounded verdicts—not a wholesale paste of `new.md`—before anyone runs Composer on 8X.1–8X.3.

## What Changes

- Harden `docs/documentation/blueprint/slice8_ci.md`: match-Dockerfile Python/apt laws, deeper 8X.1.0 inventory, optional PYTHONPATH belt, failure-category guidance; **reject** any 3.11-forever law (repo Dockerfile is `python:3.12-slim`).
- Harden `docs/documentation/blueprint/slice8_eval.md`: lock runner modes (`fixture` vs `live`), golden schema fields for trajectories, tenant two-token/fixture contract, seed-or-fixture ID strategy, evals PYTHONPATH docs.
- Harden `docs/documentation/blueprint/slice8_hitl.md`: LangGraph version/API check, resume workspace ownership gate, SSE interrupt lifecycle, locked `approval_required` JSON shape, clarify checkpointer vs automation pending queue (no mandatory second table).
- Light cross-links / law tweaks in `slice8_X.md` only if needed for consistency with the three detail files.
- Update OpenSpec main specs for the three blueprint capabilities to match the hardened requirements.
- Do **not** replace blueprints with the full `new.md` CI rewrite; do **not** implement CI/evals/HITL application code in this change.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `slice8x-ci-blueprint`: Add Dockerfile-parity (Python + apt), inventory checklist depth, service-container-as-inventory-question, PYTHONPATH hygiene; keep no-prod-secrets / no-deploy scope.
- `slice8x-eval-blueprint`: Add fixture/live mode, trajectory assert schema, tenant dual-auth or fixture, seed/fixture ID strategy, honest CI wire rules.
- `slice8x-hitl-blueprint`: Add interrupt API version discipline, resume tenant validation, SSE lifecycle, locked approval event shape, checkpointer-as-pending-state clarification.

## Impact

- Docs only under `docs/documentation/blueprint/` (primarily the three detail files; possibly `slice8_X.md`).
- OpenSpec specs under `openspec/specs/slice8x-*-blueprint/` (and optionally `slice8x-path-toc`).
- No runtime code, workflows, or `evals/` tree created yet—those remain future apply of the blueprints themselves.
- `docs/documentation/blueprint/new.md` remains a review scratchpad; it is not the source of truth and must not be copied wholesale.
