## Purpose

Detailed frontend developer / AI-agent guide for building a Next.js client against the DashNoteSystem API.

## Requirements

### Requirement: Frontend guide exists as the single entry point
The repository SHALL provide a detailed frontend developer guide at `docs/documentation/frontendguide.md` that a human or AI agent can use to build a Next.js client against the DashNoteSystem API without reading every backend blueprint first.

#### Scenario: Guide file is present and non-empty
- **WHEN** a reader opens `docs/documentation/frontendguide.md`
- **THEN** the file MUST contain a table of contents and substantive sections covering product overview, auth, domain APIs, AI streaming, errors/CORS, and a B-gate checklist

#### Scenario: Guide points to canonical backend docs
- **WHEN** a reader needs deeper backend architecture or AI laws
- **THEN** the guide MUST link to at least `system.md`, `auth.md`, and `ai.md` (under `docs/documentation/`) rather than re-copying those documents in full

### Requirement: Auth and tenancy contract for clients
The guide SHALL document how the frontend authenticates and how workspace tenancy is established so clients do not invent alternate tenant scoping.

#### Scenario: Token lifecycle documented
- **WHEN** a frontend implements login
- **THEN** the guide MUST describe `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, and `POST /auth/logout`, including that protected calls use `Authorization: Bearer <access_token>`

#### Scenario: Workspace comes from JWT only
- **WHEN** a frontend sends API requests for notes, files, or AI
- **THEN** the guide MUST state that `workspace_id` and `role` come from the JWT (`wid`, `role`) via server `RequestContext`, and clients MUST NOT pass a client-chosen workspace id to override tenancy on those routes

#### Scenario: RBAC UX implications
- **WHEN** a frontend renders notes or files for role `member` vs `owner`/`admin`
- **THEN** the guide MUST summarize notes/files visibility and mutation rules so the UI can hide or disable forbidden actions

### Requirement: Domain API map for the product UI
The guide SHALL map product UI areas to HTTP prefixes so implementers know which routers to call for each screen.

#### Scenario: Core product surfaces listed
- **WHEN** a frontend builds notes, notebooks, files, or workspace/member screens
- **THEN** the guide MUST list the relevant prefixes (`/notes`, `/notebooks`, `/files`, `/workspaces`, `/workspaces/members`) with primary operations (list/create/update/delete/upload as applicable)

#### Scenario: OpenAPI is source of truth for schemas
- **WHEN** exact request or response fields are needed
- **THEN** the guide MUST instruct readers to verify schemas against the running API OpenAPI docs (`/docs`) and MUST NOT claim frozen field lists as more authoritative than OpenAPI

### Requirement: AI chat, agent, and threads client contracts
The guide SHALL document AI surfaces as coexisting features with explicit streaming and citation rules.

#### Scenario: Chat and agent coexist
- **WHEN** a frontend designs AI UI
- **THEN** the guide MUST present `/ai/chat` and `/ai/chat/stream` (fast RAG) and `/ai/agent` and `/ai/agent/stream` (tool loop) as separate modes that MUST both remain available

#### Scenario: SSE citations from metadata only
- **WHEN** a frontend consumes a streaming AI response
- **THEN** the guide MUST require rendering answer tokens from `type: token` events and citations (or equivalent source metadata) only from the final `type: metadata` event — never by parsing citations out of the token text stream

#### Scenario: Threads for conversation continuity
- **WHEN** a frontend implements chat history
- **THEN** the guide MUST document thread list/messages endpoints under `/ai` and how optional `thread_id` continues a conversation

#### Scenario: Agent tool events for UI
- **WHEN** a frontend implements the agent view
- **THEN** the guide MUST describe how to surface tool progress (e.g. tool start/end style events) for a multi-step demo without treating the agent as a replacement for RAG chat

### Requirement: Operational UX — async work, errors, and CORS
The guide SHALL document client-visible operational behavior required for a production-quality Next.js integration.

#### Scenario: Indexing lag after create/upload
- **WHEN** a user creates a note or uploads a file
- **THEN** the guide MUST explain that search/RAG may lag until background embedding/automation finishes and SHOULD recommend an “indexing” or delayed-search UX

#### Scenario: Rate limit and LLM failure UX
- **WHEN** the API returns `429` or AI/`503` failures
- **THEN** the guide MUST require user-visible handling (including `Retry-After` for rate limits where present)

#### Scenario: CORS and base URL setup
- **WHEN** a Next.js app calls a local or production API from the browser
- **THEN** the guide MUST document setting the API base URL and ensuring the frontend origin is listed in backend `CORS_ORIGINS` for non-wildcard production configs

### Requirement: B-gate and demo checklist
The guide SHALL include an implementation checklist aligned with goal.md frontend gate B1–B7 and the stranger-test demo path.

#### Scenario: Checklist covers B1–B7
- **WHEN** a team uses the guide to plan frontend work
- **THEN** the guide MUST include checklist items for auth+CORS, notes+upload, chat SSE+citations, threads, agent UI, error states, and TLS-deployed frontend

#### Scenario: Demo path is explicit
- **WHEN** a reader prepares a product demo
- **THEN** the guide MUST list the path: register → create note → upload file → RAG question with citation → agent creates/updates note

### Requirement: Citations may name files as well as notes
The guide SHALL document the OpenAPI `Citation` shape as `note_id`, `chunk_id`, `title`, `relevance_score`, plus `source_type` (`note` | `file`) and `file_id` when the source is a file. Clients MUST render citations only from SSE `type: metadata`. When `source_type` is `file`, the client MUST link to the file detail route using `file_id` and MUST NOT treat `file_id` as a note id.

#### Scenario: File citation navigates to the file
- **WHEN** a chat stream `metadata` payload includes a citation with `source_type` `file` and a `file_id`
- **THEN** the guide MUST instruct the client to show that source and navigate to `/files/{file_id}` (or equivalent)
- **AND** MUST NOT send the user to `/notes/{file_id}`

#### Scenario: Note citation still navigates to the note
- **WHEN** a citation has `source_type` `note` (or omits `source_type` while providing `note_id`)
- **THEN** the client MUST continue to navigate to the note using `note_id`

### Requirement: Missing indexing_status is not perpetual indexing
Until OpenAPI lists `indexing_status` on notes/files, the guide MUST tell clients to use a short lag copy after create/upload and MUST NOT instruct them to show a permanent “Indexing…” state solely because the field is absent. When `FileResponse` includes `extracted_text` or `summary`, the guide MUST treat that as evidence ingest produced output the UI can show.

#### Scenario: File card without indexing_status
- **WHEN** file JSON has no `indexing_status` property
- **THEN** the guide MUST NOT require a forever “Indexing…” badge
- **AND** MUST allow a brief lag message, then idle or “ready” copy
- **AND** MUST recommend showing `summary` / extracted preview when those fields are present

#### Scenario: RAG after file indexing lag
- **WHEN** a user asks Chat about an uploaded file after background embedding has finished
- **THEN** the guide MUST state that Fast RAG and the agent search indexed files as well as notes
- **AND** MUST NOT tell the client to send `workspace_id` or `file_id` on `/ai/*` bodies
