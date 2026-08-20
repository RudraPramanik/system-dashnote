## Why

Backend AI slices **0 → 7.5** are complete, but OpenSpec has no formal baseline of what shipped versus what remains. Without that map, work drifts into more product slices instead of the stated goal: **ship + show + measure** (live API, evals, portfolio) so DashNote is hireable/demoable. This change locks the current inventory and scopes the next gate from existing docs (`goal.md`, `ship-plan.md`, `production.md`).

## What Changes

- Capture a single source of truth for **what is already built** (platform + AI slices 0–7.5, partial 7P) inside this change’s design.
- Define OpenSpec requirements for the **remaining job-search baseline** work that belongs in this repo:
  - Finish production platform steps **7P.4–7P.8** (R2 contract, deploy/runbook, smoke, CI, CD).
  - Add a **golden eval harness** (retrieval + tenant isolation) with a CLI pass/fail summary.
  - Upgrade **portfolio packaging** in-repo (README pitch, live-link placeholders, metrics table, architecture pointers).
- Do **not** start deferred slices (7A, 7R, 8 GraphRAG, 9 multi-agent, 10 metering API, 11 scale).
- Do **not** collapse `/ai/chat*` and `/ai/agent*` or bypass vector wrappers / RBAC filters.

## Capabilities

### New Capabilities

- `production-platform`: Remaining Slice 7P behaviors — R2/storage contract for worker downloads, deploy scripts + runbook, prod smoke (`scripts/smoke_prod.py`), optional `GET /health/ai`, CI on PR, CD to VPS with post-deploy smoke. Local `docker compose up` must keep working.
- `ai-eval-harness`: Golden eval cases (≥10) covering retrieval quality and tenant isolation; `evals/run_eval.py` CLI that prints pass/fail; member must not retrieve a peer’s private note.
- `portfolio-baseline`: Root README and related docs present a stranger-test pitch: live links (when available), stack, architecture pointer, eval/cost placeholders — no claim of “production-ready” without smoke/CI evidence.

### Modified Capabilities

- (none — `openspec/specs/` is empty; no existing requirement deltas)

## Impact

- **Docs / ops:** `docs/documentation/production.md`, `docs/ship-plan.md`, `docs/documentation/blueprint/goal.md`, root `readme.md`; new `docs/deployment/runbook.md`, `.env.production.example` touch-ups, `scripts/deploy/*`, `scripts/smoke_prod.py`.
- **CI/CD:** new `.github/workflows/ci.yml` and `deploy.yml` (none exist today).
- **Evals:** new `evals/` tree (golden JSONL + runner); may call live API or mocked search — must not weaken tenancy laws.
- **API (optional 7P.6):** `GET /health/ai` for soft AI/Qdrant status; hard `/health` stays Postgres + Redis only.
- **Out of this repo’s apply scope:** frontend app (B1–B7 in `goal.md`) — tracked as external dependency / non-goal for implementation here; design notes the demo gate that needs it.
- **Non-goals:** GraphRAG, multi-agent, hybrid search/reranker, automation approval UI, boiling-ocean refactors of AI modules.
