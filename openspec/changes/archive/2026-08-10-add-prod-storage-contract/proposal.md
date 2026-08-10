## Why

On the deploy-first path, 7P.0–7P.3 and thin CI (7P.7) are done; the next platform gate is the production object-storage contract (7P.4). Prod api and worker share no filesystem volume, so R2 (or S3-compatible) must be the documented contract before deploy scripts and VPS smoke. Code already uses `get_storage()`; the gap is an explicit operator-facing storage doc and closing the tracker.

## What Changes

- Add short `docs/deployment/storage.md` covering why prod needs R2/S3, env checklist, API-upload note (CORS), and a clear dev vs prod table
- Verify api upload and worker download both use `get_storage()`; apply only a minimal fix if a filesystem bypass is found
- Tighten `.env.production.example` comments for `STORAGE_BACKEND=r2` and `R2_*` if needed (values already present)
- Mark `docs/documentation/production.md` step 7P.4 as done
- Do **not** add new storage backends, change `config.py` default away from `local`, or implement 7P.5–7P.8 in this change

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `production-platform`: Clarify that the R2/object-store contract is documented in `docs/deployment/storage.md` (in addition to `.env.production.example`), and that closing 7P.4 requires that doc plus confirmation that worker/api use `get_storage()` with no shared prod volume.

## Impact

- Docs: new `docs/deployment/` tree starts with `storage.md`; tracker update in `production.md`
- Env template: optional comment polish on `.env.production.example`
- Code: likely none; possible one-line worker fix only if a `LOCAL_STORAGE_PATH` bypass is found during verify
- Out of scope: real Cloudflare R2 bucket provisioning, deploy scripts (7P.5), smoke (7P.6), CD (7P.8), evals/HITL
