## 1. system.md — map and surface

- [x] 1.1 Update the threads router row in `docs/documentation/system.md` to include list, messages, `PATCH /ai/threads/{thread_id}` rename, and delete
- [x] 1.2 Add a short Conversation auto-titles subsection (or AI features bullets): one-shot after first turn, no backfill, `ai/memory/titles.py`, SSE `title`, link `smoke-conversation-titles.md` and `ai.md`
- [x] 1.3 Expand Docker Compose / prod notes: `IMAGE=`, api healthcheck, worker→api dependency; cross-link `docs/devops-progress.md`, `docs/deployment/runbook.md`, `docs/documentation/production.md`; note HTTP-first-boot vs HTTPS
- [x] 1.4 Add pytest commands for `tests/ai/test_thread_titles.py` and `tests/ai/test_thread_rename_api.py`; optionally mention inbound smoke script if already referenced elsewhere
- [x] 1.5 Fix minor accuracy nits (e.g. postgres image tag wording) without rewriting accurate Sept 9 sections

## 2. Sibling canonical docs

- [x] 2.1 Update `docs/documentation/ai.md` with auto-title narrative and SSE `title` on chat/agent stream contracts (keep HITL and GET `/ai/test-search` as-is)
- [x] 2.2 Update `docs/documentation/lld.md` thread/chat flow notes with one-shot auto-title sequence where titles are already mentioned
- [x] 2.3 Refresh `openspec/config.yaml` context: PATCH threads, auto-title note, add `devops-progress.md` to canonical docs list; keep HTTP surface otherwise current

## 3. Ops tracker alignment

- [x] 3.1 Sync `docs/devops-progress.md` current level / Phase 1 status with `docs/documentation/blueprint/goal.md` A4 HTTP-IP PASS; leave HTTPS / later phases open

## 4. Verification

- [x] 4.1 Diff `system.md` router table against `register_routes()` in `src/main.py`
- [x] 4.2 Diff Compose service claims against `docker-compose.yml` and `docker-compose.prod.yml`
- [x] 4.3 Grep canonical docs for anti-patterns: `src/docs/`, `POST /ai/test-search` as live contract, Grafana as default local Compose on `:3001`, missing `PATCH /ai/threads`
- [x] 4.4 Confirm all new cross-links from `system.md` resolve under `docs/`
