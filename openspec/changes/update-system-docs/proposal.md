## Why

Canonical `docs/documentation/system.md` still reflects the 2026-09-09 sync and lags features and ops that shipped afterward (conversation auto-titles, thread rename, production first-boot / devops tracker). Agents and humans reading the system map miss live AI thread behavior and the current VPS deploy story.

## What Changes

- Refresh `docs/documentation/system.md` so the router table, AI surface summary, testing commands, and Compose/prod sections match `src/main.py`, both compose files, and post-sync landings.
- Document conversation auto-titles (one-shot, no backfill, SSE `title`, `ai/memory/titles.py`) and `PATCH /ai/threads/{thread_id}`; link `smoke-conversation-titles.md`.
- Add production/ops cross-links from `system.md` to `docs/devops-progress.md`, `docs/deployment/runbook.md`, and `docs/documentation/production.md` (IMAGE pull, api healthcheck, worker→api dependency, HTTP-first-boot vs HTTPS).
- Align sibling canonical docs that drifted with the same features: `ai.md` (auto-title + SSE `title`), `lld.md` (title flow), and `openspec/config.yaml` agent context.
- Sync `docs/devops-progress.md` status lines with `goal.md` evidence (A4 HTTP-IP PASS; HTTPS/A7 still open).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `canonical-docs`: System and related canonical architecture docs MUST describe conversation auto-titles (including thread rename and SSE `title`), and MUST point readers to current production/devops runbooks without inventing compose services. Docs MUST remain aligned with the mounted HTTP surface and local Compose list from the prior sync.

## Impact

- **Docs / OpenSpec context only** — no FastAPI, worker, schema, Nginx, or Compose behavior changes.
- Touched files (planned): `docs/documentation/system.md`, `ai.md`, `lld.md`; `docs/devops-progress.md`; `openspec/config.yaml`.
- `frontendguide.md` and `inbound-channels.md` stay as-is except optional light cross-links if needed; deep inbound detail remains in `docs/inbound-channels.md`.
- **Non-goals:** rewrite historical `qs*.md` / blueprint slices; change application code; restore Grafana to local Compose; implement new API features.
