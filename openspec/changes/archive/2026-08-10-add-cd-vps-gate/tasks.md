## 1. Compose image override check

- [x] 1.1 Confirm `docker-compose.prod.yml` migrate/api/worker use `image: ${IMAGE:-...}` with local `build:` fallback; add only clarifying comments or pull-policy tweaks if needed (do not rename to `DASHNOTE_IMAGE`)
- [x] 1.2 Confirm local `docker-compose.yml` and `.github/workflows/ci.yml` need no changes for this slice

## 2. CD workflow

- [x] 2.1 Create `.github/workflows/deploy.yml` with triggers: `workflow_dispatch` and `push` tags `v*` only (no auto-deploy on branch push/merge)
- [x] 2.2 Add build + push to `ghcr.io/${{ github.repository }}` (tag from git tag or dispatch input); grant `packages: write` / use `GITHUB_TOKEN` (no secrets in YAML)
- [x] 2.3 Add SSH deploy step (`VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY`): export `IMAGE`, `docker pull`, run migrate → up via `scripts/deploy/*.sh` or equivalent `docker compose -f docker-compose.prod.yml` sequence
- [x] 2.4 After deploy, run `scripts/deploy/health-check.sh` over SSH; fail the job on non-zero
- [x] 2.5 Run `python scripts/smoke_prod.py` on the runner with `SMOKE_BASE_URL` (optional `SMOKE_EMAIL` / `SMOKE_PASSWORD`); fail the job on non-zero

## 3. Docs and tracker

- [x] 3.1 Extend `docs/deployment/runbook.md` with GitHub Secrets table, CD trigger rules, GHCR login/pull notes, and production gate checklist (health + smoke + healthy compose/ps before claiming production-live)
- [x] 3.2 Mark `docs/documentation/production.md` step 7P.8 as done with pointers to `deploy.yml` and the runbook CD/gate section

## 4. Validate

- [x] 4.1 Dry-validate workflow YAML structure (triggers, no embedded secrets, jobs reference deploy helpers / smoke)
- [x] 4.2 `docker compose -f docker-compose.prod.yml config` still parses with and without `IMAGE` set
- [x] 4.3 If VPS + secrets are available: `workflow_dispatch` (or `v*` tag) completes with health-check + smoke exit 0; otherwise leave operator checklist as the remaining live gate
