## Context

DashNoteSystem ships a complete multi-tenant **backend** (FastAPI + worker). Frontend work (goal.md **B1–B7**) is intentionally out of this repo, but demo and portfolio gates require a Next.js app that talks to the live API. Today `docs/documentation/frontendguide.md` is empty; backend knowledge is split across `system.md`, `auth.md`, `ai.md`, and blueprints — too fragmented for a frontend developer or AI agent to build correctly without rediscovering SSE citation rules, JWT refresh, RBAC UX, and CORS.

**Stakeholders:** Frontend engineers / Cursor agents building a sibling Next.js app; anyone wiring CORS to prod.

**Constraint:** Guide must describe current API behavior only — no inventing endpoints; OpenAPI (`/docs`) and routers are source of truth when docs conflict.

## Goals / Non-Goals

**Goals:**

- Produce one **detailed, agent-friendly** guide at `docs/documentation/frontendguide.md`.
- Give a clear product picture: domains, tenancy, request lifecycle, and which UI surfaces map to which APIs.
- Document auth (register/login/refresh/logout), Bearer usage, token storage guidance for Next.js.
- Document domain APIs at a practical level (notes, notebooks, files, workspaces/members, AI chat/agent/threads).
- Specify SSE contracts: token vs metadata vs error; citations only from final `metadata`; chat and agent as separate UIs.
- Cover async UX (indexing lag after note/file create), rate limits (429 + `Retry-After`), LLM 503, CORS/env for local and prod.
- Align a build checklist with goal.md B1–B7 and the demo path (register → note → upload → RAG citation → agent).

**Non-Goals:**

- Scaffolding or implementing the Next.js app in this repo.
- Changing FastAPI routes, schemas, CORS code, or SSE event shapes.
- Duplicating full backend architecture laws (link to `system.md` / `ai.md` / `auth.md` instead).
- Pixel-perfect UI design system or branding guidelines.

## Decisions

### D1 — Single file, structured for humans and AI agents

**Choice:** One markdown file with a TOC, short “laws for frontend” table up front, then deep sections. Prefer tables + copy-paste fetch/SSE snippets over long prose.

**Why:** Agents and developers both need scannable contracts; empty stub already exists at the canonical path.

**Alternative:** Split into multiple files under `docs/documentation/frontend/` — rejected for now (single entry point; can split later if it grows).

### D2 — OpenAPI is normative for request/response fields; guide is normative for UX contracts

**Choice:** Guide documents method + path + purpose + auth + UX invariants (e.g. “citations from `metadata` only”). Exact field lists: point to `http://localhost/docs` or deployed `/docs`, and cite Pydantic schemas by module path when helpful.

**Why:** Schemas change; UX invariants (SSE, tenancy, RBAC) must not be rediscovered from blueprints.

**Alternative:** Freeze full JSON examples for every endpoint — rejected (rotates quickly; high maintenance).

### D3 — Target stack: Next.js App Router + browser Bearer client

**Choice:** Examples assume Next.js App Router, `fetch` from client (or Route Handlers as BFF if needed), `Authorization: Bearer <access_token>`. Recommend storing access token in memory / short-lived cookie patterns; refresh via `/auth/refresh`; never put JWT `workspace_id` override in request bodies for tenancy.

**Why:** Matches ship-plan / goal (Next.js) and backend JWT model (`wid`/`role` from token only).

**Alternative:** Prescribe a specific state library (Zustand, React Query) — optional recommendations only, not required.

### D4 — Chat and agent are two first-class UI modes

**Choice:** Guide MUST present `/ai/chat*` (fast RAG) and `/ai/agent*` (tool loop) as coexisting surfaces — separate pages or tabs, never “agent replaces chat.”

**Why:** Architecture law in `ai.md` / system docs.

### D5 — Cross-link, don’t fork backend docs

**Choice:** Related docs section at top; frontend-only content lives in `frontendguide.md`. Light one-line pointers from `system.md` and/or `goal.md` §B to the new guide during apply.

**Why:** Single ownership for frontend concerns; backend laws stay in existing files.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Guide drifts from OpenAPI after API changes | State “OpenAPI wins for schemas”; include “verify against `/docs`” note; prefer paths/methods from routers at write time |
| Over-documenting internals confuses frontend readers | Keep “laws” table short; link deep backend docs |
| Auth storage advice wrong for SSR/cookies | Document tradeoffs (httpOnly cookie BFF vs client Bearer); don’t mandate one insecure pattern |
| SSE buffering issues behind proxies | Note Nginx/`fetch` streaming caveats; cite existing slice4 client snippet as baseline |

## Migration Plan

1. Write `docs/documentation/frontendguide.md` from this design + specs.
2. Add minimal cross-links from related docs.
3. No deploy/rollback of runtime — docs-only; revert by restoring empty/previous file.

## Open Questions

- Frontend repo location (sibling vs future `frontend/` monorepo folder) — out of scope for the guide body beyond “external Next.js app”; note both are valid.
- Whether login uses OAuth2 form (`username`/`password`) vs JSON body — confirm against `auth/router.py` when writing examples.
