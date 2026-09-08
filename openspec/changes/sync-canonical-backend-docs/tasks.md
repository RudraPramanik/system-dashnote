## 1. System workflow doc

- [x] 1.1 Update `docs/documentation/system.md` router table to match `src/main.py`: add `integrations` (`/integrations`), HITL (`POST /ai/agent/resume`, `POST /ai/agent/reject`), live `GET /ai/test-search` via `ai_gateway/search.py`, and `GET /health/ai`. Note that `ai_search/router.py` POST is unmounted.
- [x] 1.2 Document CORSMiddleware, lifespan LLM env/`resolve_llm_model` (non-fatal), hard health `ok`/`unavailable` vs soft `/health/ai` `ok`/`degraded`, `pages` as ORM-only, and link `docs/inbound-channels.md` for inbound details.
- [x] 1.3 Replace `src/docs/...` pointers in `system.md` with `docs/documentation/...`. Align local Compose service list with `docker-compose.yml` (include prometheus; do not claim grafana `:3001` as a default Compose service).

## 2. AI contract doc

- [x] 2.1 Update `docs/documentation/ai.md` related-doc links away from `src/docs/`. Document HITL (`approval_required`, resume/reject), `shared/llm/fallback.py`, SSE heartbeats, and `GET /health/ai`.
- [x] 2.2 Change diagnostic search in `ai.md` to `GET /ai/test-search` (`q`, `limit`) matching `ai_gateway/search.py`. Keep `/ai/chat*` and `/ai/agent*` as coexisting surfaces.

## 3. Frontend guide

- [x] 3.1 Add an integrations section to `docs/documentation/frontendguide.md`: WhatsApp link start/confirm/unlink (Bearer JWT) and inbound email as API-key webhook, linking `docs/inbound-channels.md`.
- [x] 3.2 Document `GET /health/ai` beside `GET /health` (soft vs hard). Change the AI domain map from `POST /ai/test-search` to `GET /ai/test-search` so it matches the quick-reference section. Do not send `workspace_id` on those routes.

## 4. LLD, observe, agent context

- [x] 4.1 Fix `docs/documentation/lld.md` related links and composition notes (CORS, LLM resolve, integrations pointer, Grafana not in local Compose). Do not rewrite every still-correct §4 flow.
- [x] 4.2 Update `docs/documentation/observe.md` and `docs/observability.md` so local Compose does not require Grafana on `:3001`. Keep Prometheus `/metrics` and `:9090`.
- [x] 4.3 Update `openspec/config.yaml` `context`: product domains include `integrations`; HTTP surface includes `/integrations`, HITL agent routes, `GET /health` + `GET /health/ai`; stack line must not claim Grafana in local Compose.

## 5. Verify

- [x] 5.1 Grep canonical docs (`system.md`, `ai.md`, `lld.md`, `observe.md`, `frontendguide.md`) for `src/docs/` and for `POST /ai/test-search` as the live contract — both MUST be gone (unmounted-POST footnote in `system.md` is allowed).
- [x] 5.2 Diff the `system.md` router table against `register_routes()` in `src/main.py` and the Compose list against `docker-compose.yml`. Confirm no FastAPI/worker/nginx code changed.
