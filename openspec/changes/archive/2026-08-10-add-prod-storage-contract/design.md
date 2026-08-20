## Context

Slice 8X deploy-first order places **7P.4 (prod storage contract)** after thin CI and before deploy scripts (7P.5). Code already implements `get_storage()` with `local` | `minio` | `r2`; API routers and the automation worker download via that facade. `.env.production.example` already sets `STORAGE_BACKEND=r2` and `R2_*`. `docker-compose.prod.yml` correctly omits a shared `local_storage` volume; local `docker-compose.yml` still mounts it for `STORAGE_BACKEND=local`.

The remaining gap is operator documentation (`docs/deployment/storage.md` does not exist yet) and closing the platform tracker for 7P.4.

## Goals / Non-Goals

**Goals:**

- Publish a short storage contract doc operators can follow before VPS deploy
- Confirm (and minimally fix if needed) that api/worker never bypass `get_storage()` for file bytes
- Keep `.env.production.example` aligned and commented for R2
- Mark `production.md` 7P.4 done

**Non-Goals:**

- Provisioning a real Cloudflare R2 bucket or committing secrets
- Changing `config.py` default away from `local`
- Adding new backends beyond existing `local` / `minio` / `r2`
- Deploy scripts, smoke, CD (7P.5–7P.8)
- Frontend direct-to-R2 uploads (API uploads today; CORS note only)

## Decisions

1. **Docs-first close for 7P.4**  
   Rationale: Runtime path already matches the architecture law; inventing code churn would risk breaking local compose.  
   Alternative considered: Rewrite storage client “for clarity” — rejected unless a bypass is found.

2. **New path `docs/deployment/storage.md`**  
   Rationale: Blueprint names this file; it starts the `docs/deployment/` tree that 7P.5 runbook will join.  
   Alternative: Only expand `.env.production.example` — rejected; operators need the why/dev-vs-prod table, not just env keys.

3. **Verify then fix, don’t assume worker bugs**  
   Rationale: Grep already shows `get_storage().download(storage_key)` in automation tasks. Task list still includes an explicit verify so apply doesn’t skip the blueprint gate.  
   Alternative: Skip code touch entirely — still verify in tasks for an auditable checklist.

4. **Scope = 7P.4 only**  
   Rationale: One Composer session ≈ one platform substep; keeps review small.  
   Alternative: Bundle 7P.5 scripts — rejected for this change.

## Risks / Trade-offs

- **[Risk] Doc drifts from code** → Mitigation: Doc cites `get_storage()` / Settings field names from `config.py`; verify step before marking tracker done.  
- **[Risk] Operators think CORS setup is required now** → Mitigation: Explicit note that uploads go through the API today; CORS is future/frontend.  
- **[Risk] Someone “fixes” prod by adding a shared volume** → Mitigation: Doc and prod compose law forbid shared filesystem between api and worker on VPS.  
- **Trade-off:** Closing 7P.4 without a live R2 smoke means first real object-store proof waits for 7P.6/7P.8 — accepted on deploy-first path.

## Migration Plan

1. Land `storage.md` + any comment/tracker updates (and rare minimal code fix).  
2. No DB migration; no compose service rename.  
3. Rollback: delete/revert the doc and tracker checkbox; code rollback only if a bypass fix was applied.

## Open Questions

- None blocking apply. Real R2 credentials and bucket creation remain deferred until deploy readiness (7P.5+) and operator account setup.
