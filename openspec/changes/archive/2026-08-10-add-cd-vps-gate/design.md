## Context

7P.0–7P.7 are done: prod compose, storage contract, deploy helpers + runbook, `smoke_prod.py` + `/health/ai`, and thin PR CI (`.github/workflows/ci.yml`). There is no deploy workflow yet. `docker-compose.prod.yml` already uses `image: ${IMAGE:-dashnote-api:latest}` with a local `build:` fallback. The production-platform spec still says merge-to-main triggers CD; the Slice 8X / platform blueprint locks triggers to `v*` tags and `workflow_dispatch` only.

## Goals / Non-Goals

**Goals:**

- Ship a CD workflow that builds/pushes one app image to GHCR and deploys api/worker/migrate/nginx on the VPS via existing scripts.
- Make hard health-check + `scripts/smoke_prod.py` fail the workflow on non-zero exit.
- Document GitHub Secrets, triggers, and the production gate checklist; mark 7P.8 done in `production.md` when the workflow and docs land (real VPS proof remains the operator gate to claim “production-live”).
- Keep local `docker-compose.yml` and PR `ci.yml` behavior unchanged.

**Non-Goals:**

- Auto-deploy on every push/merge to `main` / `production`.
- Frontend, eval harness, HITL, GraphRAG, or TLS implementation.
- Changing smoke hard-gate semantics (health + auth + note create remain the gate; soft AI stays optional).
- Embedding secrets in repo files or inventing a second image env name (`DASHNOTE_IMAGE`).

## Decisions

### 1. Triggers: tag `v*` + `workflow_dispatch` only

- **Choice:** Match `slice-platform.md` 7P.8 law; update the production-platform CD requirement away from “merge to main”.
- **Why:** Accidental deploys from every merge are too risky for a thin VPS + hosted data plane; tags give explicit release points; dispatch covers first-time / hotfix.
- **Alternatives:** Deploy on every `main` push (rejected for now; can revisit later as an opt-in).

### 2. Reuse existing `IMAGE` compose override

- **Choice:** CD sets `IMAGE=ghcr.io/<owner>/<repo>:<tag>` on the VPS (or in `.env`); do not rename to `DASHNOTE_IMAGE`.
- **Why:** Already wired for migrate/api/worker; less churn.
- **Alternatives:** Rename env (rejected — breaking for any existing VPS `.env`).

### 3. Deploy path: GHCR push → SSH → existing scripts

- **Choice:** Workflow builds and pushes the Dockerfile image; SSH into VPS (`appleboy/ssh-action` or native SSH with `VPS_SSH_KEY`); `docker pull`, then prefer `scripts/deploy/migrate.sh` → `up.sh` → `health-check.sh` (or equivalent compose `-f docker-compose.prod.yml` sequence with `IMAGE` exported).
- **Why:** Keeps one operator path; scripts already fail-fast and avoid embedded secrets.
- **Alternatives:** Rebuild on VPS each deploy (slower, less reproducible); Ansible/Fleet (overkill).

### 4. Smoke runs as a hard CD gate against `SMOKE_BASE_URL`

- **Choice:** After SSH health-check succeeds, run `python scripts/smoke_prod.py` from the Actions runner (checkout already present) with `SMOKE_BASE_URL` (and optional `SMOKE_EMAIL` / `SMOKE_PASSWORD`) from GitHub Secrets/vars. Non-zero exit fails the job.
- **Why:** Matches production-platform “deploy failed if smoke exits non-zero”; runner has Python without requiring a second Python install story on the VPS for the gate; public URL validates the real edge.
- **Alternatives:** Only SSH + curl health (too weak vs existing smoke requirement); run smoke only on VPS localhost (valid fallback if no public URL yet — document both, prefer public URL when set).

### 5. Secrets surface (documented, not committed)

| Secret / var | Purpose |
|---|---|
| `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` | SSH deploy |
| `SMOKE_BASE_URL` | Post-deploy hard smoke target |
| Optional `SMOKE_EMAIL` / `SMOKE_PASSWORD` | Stable login instead of ephemeral register |
| GHCR auth | Prefer `GITHUB_TOKEN` permissions for `packages: write`; optional PAT if org policy requires |

VPS `.env` (hosted DB/Redis/Qdrant/R2/JWT/LLM) stays on the server only.

### 6. Compose / CI touch policy

- Touch `docker-compose.prod.yml` only if image pull semantics need a clarifying comment or `pull_policy`; do not break local build fallback when `IMAGE` is unset.
- Do not change `.github/workflows/ci.yml` in this change.

## Risks / Trade-offs

- **[Risk] VPS not provisioned / secrets missing → CD cannot be proven end-to-end** → Mitigation: land workflow + docs; mark tracker done for deliverables; runbook gate checklist remains the claim bar for “production-live”; `workflow_dispatch` supports first successful run when ready.
- **[Risk] GHCR private image pull fails on VPS** → Mitigation: document `docker login ghcr.io` (or deploy-time login with a read token) in runbook; prefer public package or authenticated pull.
- **[Risk] Tag/dispatch vs older “merge to main” expectation** → Mitigation: MODIFIED spec + runbook call out triggers explicitly.
- **[Risk] Smoke against public URL before DNS/TLS ready** → Mitigation: allow `http://` IP or Cloudflare origin during bootstrap; keep localhost-on-VPS path documented as manual fallback.
- **[Risk] Rollback after bad tag** → Mitigation: runbook already covers prior `IMAGE` tag + `up.sh`; CD does not auto-delete old tags.

## Migration Plan

1. Ensure VPS has repo files (`docker-compose.prod.yml`, nginx, scripts, `.env` from `.env.production.example`).
2. Add GitHub Secrets; grant packages write for GHCR.
3. Merge workflow to the default working branch.
4. First deploy via `workflow_dispatch` or `git tag v0.x.y && git push --tags`.
5. Confirm health-check + smoke exit 0; complete runbook gate checklist before claiming production-live.
6. Rollback: set previous `IMAGE` tag on VPS and re-run `up.sh` / prior compose up.

## Open Questions

- Exact GHCR image name (`ghcr.io/<github.repository>` vs shorter `dashnote`) — default to `ghcr.io/${{ github.repository }}` unless operator prefers otherwise at apply time.
- Whether first production claim waits on HTTPS or allows HTTP-only gate during TLS option selection (docs already treat TLS as a decision, not a blocker for 7P.8 scripts).
