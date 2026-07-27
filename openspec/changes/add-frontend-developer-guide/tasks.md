## 1. Research & outline

- [x] 1.1 Confirm current auth request shapes from `src/auth/router.py` (register/login form vs JSON, refresh/logout headers)
- [x] 1.2 Confirm AI request/SSE event shapes from `src/ai_routes/chat.py`, `agent.py`, `threads.py` (and search router method/path)
- [x] 1.3 Sketch TOC for `docs/documentation/frontendguide.md` matching design sections (overview, laws, auth, domains, AI, ops, B-gate)

## 2. Write the guide

- [x] 2.1 Write product overview + frontend laws table + links to `system.md` / `auth.md` / `ai.md` / OpenAPI
- [x] 2.2 Write auth & tenancy section (token lifecycle, Bearer, JWT `wid`/`role`, RBAC UX for notes/files)
- [x] 2.3 Write domain API map (`/notes`, `/notebooks`, `/files`, `/workspaces`, `/workspaces/members`) with primary operations
- [x] 2.4 Write AI section: chat vs agent coexistence, SSE token/metadata/error rules, threads, agent tool-progress UX, copy-paste stream example
- [x] 2.5 Write operational UX: indexing lag, 429/`Retry-After`, 503 LLM, CORS/`CORS_ORIGINS`, API base URL for Next.js
- [x] 2.6 Write B1–B7 checklist + demo path (register → note → upload → RAG citation → agent)

## 3. Cross-links & verify

- [x] 3.1 Add a one-line pointer from `docs/documentation/system.md` and/or `docs/documentation/blueprint/goal.md` §B to `frontendguide.md`
- [x] 3.2 Review guide against live OpenAPI (or router sources) for path/method accuracy; fix any mismatches
- [x] 3.3 Spot-check that specs scenarios (citations-from-metadata, chat/agent coexist, JWT tenancy, B-gate) are all covered in the guide
