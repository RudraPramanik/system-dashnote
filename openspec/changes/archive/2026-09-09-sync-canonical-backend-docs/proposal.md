## Why

Canonical backend docs (`system.md`, `ai.md`, `lld.md`, `observe.md`) and the agent context in `openspec/config.yaml` lag the live FastAPI surface. Readers and coding agents still follow `src/docs/` paths that do not exist, miss `/integrations` and HITL agent routes, and treat Grafana as a local Compose service. That drift now produces wrong routing, health, and client contracts.

## What Changes

- Refresh `docs/documentation/system.md` so the router table, lifespan, middleware, health, Compose, and module map match `src/main.py` and current `docker-compose.yml`.
- Refresh `docs/documentation/ai.md` for HITL (`/ai/agent/resume`, `/ai/agent/reject`, `approval_required`), LLM fallback, SSE heartbeats, live `GET /ai/test-search`, and `GET /health/ai`.
- Fix broken `src/docs/...` cross-links in canonical docs (`system.md`, `ai.md`, `lld.md`, `observe.md`, related pointers) to `docs/documentation/...`.
- Align `docs/documentation/frontendguide.md` with the live API: integrations (WhatsApp link + inbound pointer), `GET /health/ai`, and **GET** (not POST) `/ai/test-search`.
- Update `docs/documentation/lld.md` and observability docs so Grafana is not claimed as a running local Compose service (Prometheus remains; Grafana Cloud / provisioning files may still exist).
- Update `openspec/config.yaml` context (HTTP surface, product domains, stack notes) so future OpenSpec prompts match the code.
- Point to `docs/inbound-channels.md` as the deep inbound runbook; do not duplicate it.

## Capabilities

### New Capabilities

- `canonical-docs`: Canonical architecture docs under `docs/documentation/` (especially `system.md` and `ai.md`) MUST describe the mounted HTTP surface, current local Compose services, and working in-repo links. They MUST NOT send readers to `src/docs/`.

### Modified Capabilities

- `frontend-developer-guide`: The frontend guide MUST document live client-facing routes that exist today (integrations WhatsApp link, health including soft `/health/ai`, diagnostic `GET /ai/test-search`) and MUST NOT present the unmounted `POST /ai/test-search` as the product contract.

## Impact

- **Docs only** — no FastAPI, worker, schema, or Nginx behavior changes.
- Touched files: `docs/documentation/system.md`, `ai.md`, `lld.md`, `observe.md`, `frontendguide.md`; `docs/observability.md` (Grafana/Compose claims); `openspec/config.yaml`.
- Tenancy/RBAC: unchanged. Inbound email stays API-key/HMAC (not JWT tenancy override). WhatsApp link routes stay JWT-scoped. Soft `/health/ai` stays out of the hard deploy gate.
- **Non-goals:** rewrite `qs.md` / `qs2.md` / `qs3.md`; rewrite historical slice blueprints; delete unmounted `src/ai_search/router.py`; restore Grafana to local Compose; implement new API features.
