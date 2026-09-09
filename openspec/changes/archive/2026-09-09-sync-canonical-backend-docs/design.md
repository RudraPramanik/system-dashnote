## Context

See `proposal.md` for why. Specs: `canonical-docs` + `frontend-developer-guide`.

Constraints:

- Source of truth for HTTP is `register_routes()` in `src/main.py` plus health metrics exposed on the app. Narrative docs must follow that, not historical slice notes.
- Source of truth for local stack is `docker-compose.yml` (prometheus yes; grafana service absent). `monitoring/grafana/` may remain on disk.
- `docs/inbound-channels.md` already documents email/WhatsApp ingest. Canonical docs should link it, not fork a second runbook.
- `src/ai_search/router.py` (`POST /ai/test-search`) is **not** mounted. Live diagnostic search is `GET /ai/test-search` in `ai_gateway/search.py`.
- `src/pages/` is ORM/versioning only — no router in `main.py`.
- This change is documentation + OpenSpec agent context. API, worker, Nginx, and Alembic stay untouched.

## Goals / Non-Goals

**Goals:**

- One pass that makes `system.md` / `ai.md` / `frontendguide.md` agree with mounted routes.
- Replace dead `src/docs/` pointers in the canonical set with `docs/documentation/` (and `docs/observability.md` for the human observe runbook).
- Refresh `openspec/config.yaml` `context` so later changes inherit the live HTTP surface (integrations, HITL, `/health/ai`, no Grafana-in-compose claim).

**Non-Goals:**

- Rewriting interview Q&A (`qs.md`, `qs2.md`, `qs3.md`) or historical slice blueprints except accidental broken links inside the canonical files we already open.
- Deleting `ai_search/router.py` or restoring Grafana to Compose.
- Expanding LLD into a full rewrite of every §4.x flow (add missing routers + fix links + Compose/Grafana; leave still-correct flows).

## Decisions

### D1 — Edit the canonical set in place; keep inbound as a linked runbook

Update these files as the contract:

| File | Owns |
|------|------|
| `docs/documentation/system.md` | Router table, lifespan, middleware (incl. CORS), health, Compose, modules |
| `docs/documentation/ai.md` | AI laws, HITL, fallback, GET test-search, `/health/ai` |
| `docs/documentation/frontendguide.md` | Client map + HITL (already present) + integrations + health/ai + GET test-search |
| `docs/documentation/lld.md` | Related-doc links, composition notes, Grafana/Compose, integrations pointer |
| `docs/documentation/observe.md` + `docs/observability.md` | Drop “Grafana on :3001 via `docker compose up`” as current local fact |
| `openspec/config.yaml` | Agent `context` HTTP/modules/stack |

`docs/inbound-channels.md` stays the inbound operator doc. `system.md` gets a short integrations row + link.

**Alternative considered:** Merge inbound into `system.md` — rejected; that file is already a workflow map, and inbound has provider/n8n specifics.

### D2 — Document live GET search; do not delete the unmounted POST module

`system.md`, `ai.md`, and `frontendguide.md` MUST all say `GET /ai/test-search?q=&limit=`. Frontend guide currently contradicts itself (AI map says POST; quick reference says GET). Fix the map; keep OpenAPI as schema authority.

Leave `src/ai_search/router.py` in the tree. A one-line “unmounted / not the live contract” note in `system.md` is enough so agents do not “fix” docs back to POST.

**Alternative considered:** Delete the dead router in this change — rejected (code change; separate cleanup).

### D3 — Match Compose reality for Grafana; keep Prometheus

Local `docker-compose.yml` services: `db`, `redis`, `nginx`, `migrate`, `api`, `worker`, `qdrant`, `prometheus`. No `grafana` service. Docs that say “Compose grafana :3001” are stale. Record Prometheus `:9090` + `/metrics`. Mention Grafana Cloud / leftover `monitoring/grafana/` as non-default local UI.

**Alternative considered:** Re-add Grafana to Compose as part of this change — rejected (infra, not docs sync).

### D4 — Lifespan and health wording follow code

`system.md` lifespan today skips: `configure_litellm_env` + `resolve_llm_model` (non-fatal) before ARQ/Qdrant/checkpointer. CORSMiddleware is registered; document it.

Hard `GET /health` returns `status: "ok"` or `"unavailable"` with **503** when db/redis fail — not the word `"degraded"` (that label is used on `/health/ai`). Align the system doc with `core/health.py`.

### D5 — Pages stay “internal ORM”

List `pages` under modules as tenant ORM used by notebooks/worker imports, **no HTTP prefix**. Do not invent `/pages` routes.

### D6 — Process ownership

| Work | Owner |
|------|--------|
| Narrative accuracy | Docs files listed in D1 |
| Agent prompt accuracy | `openspec/config.yaml` `context` |
| API / worker | Unchanged |

No Alembic, settings, or Qdrant collection changes.

## Risks / Trade-offs

- **[Risk] Historical blueprints still say `src/docs/` and Grafana-in-compose** → Mitigation: only fix links in files we edit; blueprints remain build history. A follow-up can grep the rest.
- **[Risk] `openspec/config.yaml` YAML `context:` is a large string; easy to drift again** → Mitigation: treat the HTTP surface bullet list as the checklist against `main.py` at apply time.
- **[Risk] Frontend authors still miss inbound** → Mitigation: short domain-map section + link to `docs/inbound-channels.md`.
- **Trade-off:** Docs describe current Compose (no Grafana) rather than the older “full observability stack” story. Honesty beats a nicer diagram.

## Migration Plan

Docs-only. No deploy. Rollback = git revert of the markdown/`config.yaml` commit.

## Open Questions

None that block apply. Whether to delete `ai_search/router.py` or restore Grafana is out of this change.
