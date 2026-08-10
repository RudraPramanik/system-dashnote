# Production storage contract (R2)

> Platform step **7P.4**. Code entrypoint: `get_storage()` in `src/core/storage/client.py`.  
> Settings names live in `src/config.py`. Never commit real secrets — use VPS `.env` from `.env.production.example`.

## Why prod needs object storage

On the VPS, **api** and **worker** are separate containers. They do **not** share a filesystem volume for uploads.

- Upload path: API receives the file → `get_storage().upload(...)` → object key stored as `files.storage_key` in Postgres.
- Worker path: automation loads the row → `get_storage().download(storage_key)` → bytes for parsing / indexing.

If both used a local disk path without a shared volume, the worker would never see API uploads. **R2 (or another S3-compatible backend)** is the prod contract so both services read/write the same object store via credentials in `.env`.

Do **not** “fix” prod by adding a shared Docker volume between api and worker — that breaks the thin-compute / hosted-data-plane model.

## Env checklist (prod)

| Variable | Purpose |
|----------|---------|
| `STORAGE_BACKEND` | Must be `r2` on VPS (also supports `minio` for S3-compatible self-host; not the default prod path) |
| `R2_ENDPOINT` | Cloudflare R2 S3 API endpoint, e.g. `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY_ID` | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | R2 API token secret |
| `R2_BUCKET` | Bucket name (e.g. `dashnote-prod`) |

Template: `.env.production.example`. Local defaults stay in `.env.example` / `config.py` (`STORAGE_BACKEND=local`).

## Uploads and CORS

**Today:** clients upload through the **API** (`/files` routes). The API writes to storage via `get_storage()`. Browser → R2 direct upload is **not** required.

If a future frontend uploads directly to the bucket, configure Cloudflare R2 **CORS** for that origin. Until then, no bucket CORS setup is needed for the API-upload path.

## Local vs prod

| | Local (`docker compose`) | Prod (`docker-compose.prod.yml`) |
|--|--------------------------|----------------------------------|
| `STORAGE_BACKEND` | `local` | `r2` |
| Bytes location | Compose volume `local_storage` → `/app/storage` | Cloudflare R2 bucket |
| Shared volume api↔worker | Yes (`local_storage`) | **No** — object store only |
| Metadata | Postgres `files.storage_key` | Same |

## Operator checks

1. VPS `.env` has `STORAGE_BACKEND=r2` and filled `R2_*` values.
2. Prod compose does **not** mount a shared upload volume on api/worker.
3. After deploy, upload a file via API and confirm worker automation can download it (full smoke comes in 7P.6 / 7P.8).
