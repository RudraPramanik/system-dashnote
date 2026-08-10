# VPS deploy runbook

> Platform step **7P.5**. Compose file: `docker-compose.prod.yml` only.  
> Storage contract: [`storage.md`](storage.md). Never commit a filled `.env`.  
> Do **not** claim production-live until **7P.8** smoke passes.

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

## Windows / PowerShell notes (local operators)

Deploy **scripts are bash for the Linux VPS**. On Windows:

- Prefer WSL2 or SSH into the VPS and run the bash helpers there.
- For local full-stack development, keep using `docker compose up -d --build` (default `docker-compose.yml`) — not these prod scripts.
- Manual prod-compose validation from PowerShell (no secrets required for config parse):

```powershell
docker compose -f docker-compose.prod.yml config
```

Ensure shell scripts keep **LF** line endings (see `.gitattributes` for `scripts/deploy/*.sh`). After clone on Linux: `chmod +x scripts/deploy/*.sh`.

## Related

- [`storage.md`](storage.md) — R2 / object storage contract (7P.4)
- [`../documentation/production.md`](../documentation/production.md) — platform tracker
- `docker-compose.prod.yml` — api, worker, migrate, nginx, optional prometheus
