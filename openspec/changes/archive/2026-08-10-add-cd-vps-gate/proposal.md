## Why

Slices 7P.0–7P.7 are complete (prod compose, storage, deploy scripts/runbook, smoke, thin CI), but there is still no CD path that ships a tagged image to a VPS and proves the stack with health + smoke. Without 7P.8, we cannot claim production-live or unlock the next deploy-first milestones (min frontend → evals → HITL).

## What Changes

- Add `.github/workflows/deploy.yml` that builds/pushes the app image to GHCR and SSH-deploys to the VPS using existing `scripts/deploy/*` helpers.
- Trigger CD on `workflow_dispatch` and `push` of version tags (`v*`) only — **not** every push/merge to the default branch (aligns with `slice-platform.md` 7P.8 law; updates the current production-platform CD requirement).
- Ensure prod compose continues to accept a registry image via the existing `IMAGE` env override so the VPS can pull without rebuilding.
- Extend `docs/deployment/runbook.md` with GitHub Secrets, CD trigger rules, and a production gate checklist; mark `docs/documentation/production.md` step 7P.8 done when the gate is documented and the workflow lands.
- Fail the deploy workflow if hard health-check or `scripts/smoke_prod.py` exits non-zero.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Replace “deploy on merge to main” with explicit tag/`workflow_dispatch` CD; require GHCR image push + SSH VPS update via deploy helpers; require hard gate (health-check + smoke) with non-zero failure; document secrets and gate checklist in the runbook; track 7P.8 completion in `production.md`.

## Impact

- **New:** `.github/workflows/deploy.yml`
- **Likely touch:** `docker-compose.prod.yml` only if `IMAGE`/build override needs clarifying; `docs/deployment/runbook.md`; `docs/documentation/production.md`
- **Reuse:** `scripts/deploy/migrate.sh`, `up.sh`, `health-check.sh`, `scripts/smoke_prod.py`, existing GHCR/`IMAGE` patterns
- **Secrets (operator-configured, not in repo):** `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, optional registry token; smoke base URL / credentials as documented
- **Out of scope:** Frontend, eval harness, HITL, GraphRAG, changing local `docker-compose.yml` or PR `ci.yml` behavior, implementing TLS (docs-only remains)
- **Gate:** Feature slices 8+ and chosen-path evals/HITL stay blocked until this production gate passes on a real VPS
