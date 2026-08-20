## Why

The backend is demo-ready (auth, notes, files, RAG chat, threads, agent), but `docs/documentation/frontendguide.md` is empty and frontend work (goal.md B1–B7) lives outside this repo. Next.js developers and AI agents lack a single, detailed contract for auth, tenancy, API shapes, SSE streaming, RBAC UX, and error handling — so UI work risks CORS mistakes, wrong citation parsing, and broken workspace scoping.

## What Changes

- Author a comprehensive **frontend developer / AI-agent guide** at `docs/documentation/frontendguide.md`.
- Cover everything a Next.js App Router client needs: product map, auth & token lifecycle, workspace/RBAC rules, REST surface by domain, AI chat/agent SSE contracts, file upload flows, rate-limit/error UX, CORS & env setup, and a B1–B7 build checklist aligned with `goal.md`.
- Cross-link existing canonical docs (`system.md`, `auth.md`, `ai.md`, OpenAPI) instead of duplicating backend internals.
- Do **not** scaffold or ship a Next.js app in this change — documentation only.

## Capabilities

### New Capabilities

- `frontend-developer-guide`: A single, detailed guide for humans and AI agents building a Next.js frontend against the DashNoteSystem API — auth, tenancy, domain APIs, SSE AI contracts, errors, and the B-gate checklist.

### Modified Capabilities

- (none — no existing `openspec/specs/` requirements change; this is a new documentation capability)

## Impact

- **Docs:** `docs/documentation/frontendguide.md` (primary deliverable); light cross-links from related docs if needed (`system.md`, `goal.md`, root README).
- **Consumers:** External Next.js app (sibling repo or future `frontend/`); Cursor/AI agents building UI against prod/local API.
- **APIs / code:** No backend behavior changes. Guide must match current FastAPI contracts (`/auth`, `/notes`, `/files`, `/notebooks`, `/workspaces`, `/ai/*`).
- **Non-goals:** Implementing the Next.js app, changing CORS defaults in code, or altering SSE/API schemas.
