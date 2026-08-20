## Why

Platform steps 7P.0–7P.3 are done and the deploy-first ship path locks **thin CI (7P.7 / 8X.1)** as the next calendar work before finishing VPS deploy. PRs currently have no automated seatbelt — regressions can land without pytest or a Docker image build — and we need that gate without production secrets or deploy jobs.

## What Changes

- Add GitHub Actions thin CI: inventory-first, then `.github/workflows/ci.yml` with pytest + `docker build` only
- Align CI Python/apt/requirements to the repo `Dockerfile` (currently `python:3.12-slim` + `libmagic1` + `requirements/base.txt`)
- Keep local `docker-compose.yml` and app source untouched unless inventory proves a one-line fix is required
- Mark `docs/documentation/production.md` 7P.7 complete when CI is green
- Do **not** add CD, SSH, VPS secrets, eval harness, HITL, or required live LLM/Qdrant keys

## Capabilities

### New Capabilities
- `thin-ci`: PR GitHub Actions workflow that runs pytest and Docker image build without production or live AI secrets

### Modified Capabilities
- *(none)* — `slice8x-ci-blueprint` already documents the executable prompts; this change implements that behavior in the repo, not new blueprint requirements

## Impact

- New: `.github/workflows/ci.yml`
- Reads (no rewrite unless broken): `tests/conftest.py`, `pytest.ini`, `Dockerfile`, `requirements/base.txt` / related requirements
- Tracker: `docs/documentation/production.md` (7P.7 ✅)
- Systems: GitHub Actions runners only; no VPS, no hosted prod credentials
- Out of scope: 7P.4–7P.6, 7P.8 CD, frontend, evals (8X.2), HITL (8X.3)
