## 1. Verify R2 code path

- [x] 1.1 Confirm `src/files/router.py` (and related upload paths) use `get_storage()` for file bytes — no direct filesystem path construction for uploads
- [x] 1.2 Confirm `src/worker/automation/tasks.py` downloads via `get_storage().download(storage_key)` — no `LOCAL_STORAGE_PATH` bypass
- [x] 1.3 If a bypass is found, apply a minimal fix to route through `get_storage()` only (no backend redesign)

## 2. Document storage contract

- [x] 2.1 Create `docs/deployment/storage.md` covering: why prod needs R2/S3 (no shared api/worker volume), env vars checklist (`STORAGE_BACKEND`, `R2_*`), API-upload note (CORS only if frontend uploads later), and a local-dev vs prod table
- [x] 2.2 Ensure `.env.production.example` has `STORAGE_BACKEND=r2` and all `R2_*` vars with clear comments (do not change `config.py` default away from `local`)

## 3. Validate and close gate

- [x] 3.1 Run `python -m pytest tests/files -q` (or note blockers) to confirm local storage behavior still healthy
- [x] 3.2 Confirm `docker-compose.yml` still mounts `local_storage` for api/worker and `docker-compose.prod.yml` does not add a shared file volume
- [x] 3.3 Mark `docs/documentation/production.md` step 7P.4 as done
