# VPS deploy runbook

> Platform steps **7P.5** (scripts) + **7P.8** (CD gate). Compose file: `docker-compose.prod.yml` only.  
> Storage contract: [`storage.md`](storage.md). Never commit a filled `.env`.  
> Do **not** claim production-live until the **production gate checklist** below passes (hard health + smoke).

## 1. Prerequisites checklist

| Item | Expected |
|------|----------|
| VPS OS | Ubuntu 22.04+ (or equivalent Linux) |
| Docker | Docker Engine + **Compose plugin** (`docker compose version`) |
| Hosted Postgres | `DATABASE_URL` reachable from the VPS |
| Hosted Redis | `REDIS_URL` reachable from the VPS |
| Qdrant Cloud | `QDRANT_URL` (+ key if required); soft at boot — see 7P.3 |
| Object storage | Cloudflare R2 (or S3-compatible) per [`storage.md`](storage.md) |
| DNS | A record (or Cloudflare proxy) → VPS public IP |
| Secrets | Copy from `.env.production.example` → VPS `.env` (not in git) |

**Compose law:** On the VPS always use `-f docker-compose.prod.yml`. Never run the local full-stack `docker-compose.yml` in production (it expects in-compose db/redis/qdrant).

## 2. First-time VPS setup

```bash
# On the VPS, from the repo root (clone or copy compose + nginx + monitoring files)
git clone <repo-url> dashnotesystemv1
cd dashnotesystemv1

cp .env.production.example .env
# Edit .env — fill DATABASE_URL, REDIS_URL, QDRANT_*, JWT secrets, R2_*, LLM keys, etc.

chmod +x scripts/deploy/*.sh

docker compose -f docker-compose.prod.yml build
./scripts/deploy/migrate.sh
./scripts/deploy/up.sh
./scripts/deploy/health-check.sh
```

Optional observability (Prometheus profile only):

```bash
docker compose -f docker-compose.prod.yml --profile observability up -d prometheus
```

## 3. Deploy sequence (every release)

From the repo root on the VPS:

```bash
git pull
# Or: docker pull "$IMAGE" when using a pre-built registry image + IMAGE= in .env

./scripts/deploy/migrate.sh
./scripts/deploy/up.sh
./scripts/deploy/health-check.sh
```

| Script | Role |
|--------|------|
| `scripts/deploy/migrate.sh` | One-shot `alembic upgrade head` via the `migrate` service |
| `scripts/deploy/up.sh` | Start `api`, wait for health, then `worker` + `nginx` |
| `scripts/deploy/health-check.sh` | `GET http://127.0.0.1/health` (nginx edge); exit non-zero on failure |

Scripts read credentials only via compose `env_file: .env`. They never embed secrets.

## 4. Rollback

1. Check out or pull the previous known-good commit **or** set `IMAGE` / retag to the previous image.
2. Rebuild or `docker compose -f docker-compose.prod.yml pull` as appropriate.
3. Re-run:

```bash
./scripts/deploy/migrate.sh   # only if you must re-apply forward migrations; prefer forward-fix when possible
./scripts/deploy/up.sh
./scripts/deploy/health-check.sh
```

If a bad image is running, prefer pinning `IMAGE=<previous_tag>` in `.env` and re-running `up.sh` rather than inventing ad-hoc `docker run` commands.

## 5. TLS options (pick one — not implemented in 7P.5)

`docker-compose.prod.yml` publishes **HTTP :80** via nginx. HTTPS is an operator decision:

| Option | Notes |
|--------|--------|
| **Cloudflare SSL** | Proxy DNS through Cloudflare; Flexible or Full (Full preferred once origin has a cert). Fastest path for a demo URL. |
| **Caddy** | Replace or sit in front of nginx; automatic Let's Encrypt. Documented as a common thin-VPS choice. |
| **Certbot + nginx** | Obtain certificates on the host; extend nginx to listen on 443 and mount certs (compose currently comments 443 — wire when chosen). |

This section is decision documentation only. Shipping a specific TLS setup is deferred (typically with 7P.8 / real VPS).

## 6. Optional observability profile

```bash
docker compose -f docker-compose.prod.yml --profile observability up -d prometheus
```

Grafana stays off-VPS (e.g. Grafana Cloud remote_write). See compose comments on the `prometheus` service.

## 7. Post-deploy smoke (7P.6)

After `health-check.sh` (or against a public URL), run the lean hard gate:

```bash
# On VPS (nginx edge) or against a public API URL
python scripts/smoke_prod.py
# Or:
SMOKE_BASE_URL=http://127.0.0.1 python scripts/smoke_prod.py
SMOKE_BASE_URL=https://api.example.com python scripts/smoke_prod.py
```

**Hard gate (must exit 0):** `GET /health` → auth register (or login) → notebook + note create.

| Env / flag | Purpose |
|------------|---------|
| `SMOKE_BASE_URL` / `--base-url` | API edge (default `http://127.0.0.1`) |
| `SMOKE_EMAIL` + `SMOKE_PASSWORD` | Login instead of ephemeral register |
| `--with-ai` / `SMOKE_SOFT_AI=1` | Soft checks only: `GET /health/ai`, optional file upload poll — **never** fails the hard exit |

Do **not** commit real credentials. Soft AI / Qdrant is **not** part of the deploy hard gate (`GET /health/ai` is informational).

Broader local E2E (optional): `python scripts/e2e_docker_smoke.py`.

## 8. CD workflow (7P.8)

Automated deploy lives at [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml).

### Triggers (explicit only)

| Event | Deploys? |
|-------|----------|
| `workflow_dispatch` (Actions UI / API) | Yes |
| Push tag matching `v*` (e.g. `v0.1.0`) | Yes |
| Push / merge to `main`, `production`, or any branch | **No** |

### GitHub Secrets / vars

Configure under the repo **Settings → Secrets and variables → Actions**. Never put these in git.

| Name | Required | Purpose |
|------|----------|---------|
| `VPS_HOST` | Yes | VPS hostname or IP for SSH |
| `VPS_USER` | Yes | SSH user |
| `VPS_SSH_KEY` | Yes | Private key (PEM) for that user |
| `SMOKE_BASE_URL` | Yes | Public (or reachable) API edge for post-deploy smoke, e.g. `https://api.example.com` or `http://<vps-ip>` |
| `SMOKE_EMAIL` | No | Stable smoke login (otherwise ephemeral register) |
| `SMOKE_PASSWORD` | No | Password for `SMOKE_EMAIL` |
| `GHCR_TOKEN` | No | PAT / token with `read:packages` so the VPS can `docker login ghcr.io` when the image is private |
| `VPS_APP_DIR` (Actions **variable**) | No | Absolute path to the repo on the VPS (default `/opt/dashnote`) |

GHCR **push** from Actions uses `GITHUB_TOKEN` with `packages: write` (no extra secret required for push).

### GHCR pull on the VPS

CD sets `IMAGE=ghcr.io/<owner>/<repo>:<tag>` (lowercase) and runs `docker pull` before migrate/up.

1. First-time: clone or sync repo files to `VPS_APP_DIR` (compose, nginx, scripts, `.env`).
2. If the GHCR package is **private**, either:
   - set `GHCR_TOKEN` so the workflow logs the VPS into `ghcr.io`, or
   - once on the VPS: `echo "$TOKEN" | docker login ghcr.io -u USER --password-stdin`
3. Prefer keeping the package private and using a read token over embedding credentials in `.env`.

Manual equivalent:

```bash
export IMAGE=ghcr.io/<owner>/<repo>:v0.1.0
docker pull "$IMAGE"
./scripts/deploy/migrate.sh
./scripts/deploy/up.sh
./scripts/deploy/health-check.sh
SMOKE_BASE_URL=https://api.example.com python scripts/smoke_prod.py
```

### Production gate checklist

Complete **all** before claiming production-live or starting post-7P.8 feature work:

- [ ] `./scripts/deploy/health-check.sh` (or `curl` to the public `/health`) → success
- [ ] `SMOKE_BASE_URL=... python scripts/smoke_prod.py` → exit 0
- [ ] `docker compose -f docker-compose.prod.yml ps` — api/worker/nginx healthy / up
- [ ] Worker logs: no crash loop (`docker compose -f docker-compose.prod.yml logs worker --tail 100`)
- [ ] Qdrant Cloud shows collections (soft — informational)
- [ ] After a test upload, R2 (or configured object store) has objects (soft — informational)

CD fails the GitHub Actions job if SSH health-check or runner smoke exits non-zero. A green workflow is necessary but operators should still tick the checklist on a real VPS once.

## Windows / PowerShell notes (local operators)

Deploy **scripts are bash for the Linux VPS**. On Windows:

- Prefer WSL2 or SSH into the VPS and run the bash helpers there.
- For local full-stack development, keep using `docker compose up -d --build` (default `docker-compose.yml`) — not these prod scripts.
- Manual prod-compose validation from PowerShell (no secrets required for config parse):

```powershell
docker compose -f docker-compose.prod.yml config
```

Ensure shell scripts keep **LF** line endings (see `.gitattributes` for `scripts/deploy/*.sh`). After clone on Linux: `chmod +x scripts/deploy/*.sh`.

## Failure-mode notes (demo / ops talk track)

| Symptom | Likely cause | What to do / say |
|---------|--------------|------------------|
| Chat answers “I could not find relevant information…” | Empty retrieval (threshold / no embeds / wrong workspace) | Check note was embedded (worker logs); wait for embed lag; confirm JWT workspace; Langfuse may show `empty_retrieval` score |
| `503` on `/ai/chat*` or `/ai/agent*` | LLM provider down / keys / rate limit | Message is user-safe; retry; FE shows AI-unavailable copy; use `/health` (hard) vs AI soft deps |
| Search misses a note just created | Embed lag (ARQ worker queue) | Wait `wait_embed_sec`-class delay; worker healthy; Qdrant soft boot does not block API but search needs indexer |
| Agent returns `approval_required` | HITL before `create_note` / `update_note` | Call `POST /ai/agent/resume` or `/ai/agent/reject` with same `thread_id`; FE polish optional — see `scripts/smoke_hitl.py` |

Also linked from [`../interview-talk-track.md`](../interview-talk-track.md).

## Related

- [`storage.md`](storage.md) — R2 / object storage contract (7P.4)
- [`../documentation/production.md`](../documentation/production.md) — platform tracker
- [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) — CD (7P.8)
- `docker-compose.prod.yml` — api, worker, migrate, nginx, optional prometheus (`IMAGE=` for registry pulls)
- [`scripts/smoke_hitl.py`](../../scripts/smoke_hitl.py) — local HITL approve/reject smoke
