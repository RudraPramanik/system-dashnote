## Why

File ingest already works: a 1MB PDF extracts text, the worker upserts `files_chunks`, and Chat still answers as if the document does not exist. `WorkspaceVectorSearch` only queries `notes_chunks` (Slice 7 deferred file search to Slice 8). The Files UI also looks stuck on “Indexing…” because `FileResponse` omits worker fields and the client treats a missing `indexing_status` as processing forever.

## What Changes

- Extend `WorkspaceVectorSearch.search()` (the only Qdrant search interface) to query **both** `notes_chunks` and `files_chunks`, merge by score, and apply the same JWT `workspace_id` + `build_rbac_filter()` on every collection. Do **not** upsert files into `notes_chunks`.
- Carry `source_type` (`note` | `file`) and `file_id` through `SearchResult`, RAG citations, `/ai/test-search`, and OpenAPI `Citation`. Keep `note_id` for notes. **Not BREAKING** if clients ignore unknown fields; DashNotes citation chips MUST start routing file sources after OpenAPI regen.
- Point `/ai/chat*`, `/ai/agent*` (`search_notes` tool + system prompt), and empty-retrieval copy at workspace **notes and files**. Chat and agent stay separate routes.
- Include `summary`, `tags`, and truncated `extracted_text` on file JSON so the client can show real ingest output without inventing `indexing_status`.
- Harden `extract_json_blob` / structured parse so `generate_file_metadata` survives extra `{` / salvageable JSON (live fail 2026-09-03).
- Update `docs/documentation/ai.md` and `frontendguide.md` (citation shape, file RAG, indexing lag vs missing status).

## Capabilities

### New Capabilities

- `rag-retrieval`: Dual-collection semantic search, file-aware citations, chat/agent grounded on indexed files.
- `files`: File API surfaces automation fields; metadata job parse is salvage-tolerant.

### Modified Capabilities

- `frontend-developer-guide`: Citation OpenAPI fields include `source_type` / `file_id`; RAG may cite files; missing `indexing_status` MUST NOT mean perpetual indexing; file detail SHOULD show summary/extracted text when present.

## Impact

- **Code:** `src/ai/retrieval/wrapper.py`, `rag_service.py`, `ai/prompts/rag.py`, `ai/tools/note_tools.py`, `ai/workflows/workspace_assistant.py`, `ai_gateway/search.py`, `files/schemas.py` + `files/router.py`, `shared/llm/structured.py`. Worker index path unchanged except metadata parse reliability.
- **API:** `Citation` gains `source_type` and optional `file_id`. `FileResponse` gains `summary`, `tags`, `extracted_text` (list MAY omit or null `extracted_text` to keep payloads small). No new routes. No `file_id` on chat/agent bodies (tenant still JWT-only).
- **Qdrant:** Read `files_chunks` on search; writes stay on `FileVectorIndexer` / worker.
- **Tenancy:** Unchanged. `workspace_id` never from the client. Member still sees own private files + public; owner/admin see workspace files.
- **Tests:** Dual-collection merge + RBAC; citation mapping; FileResponse fields; JSON salvage. No live LLM/Qdrant required.
- **Sibling DashNotes:** Out of this repo’s edit root. After apply, regenerate OpenAPI types and route file citations to `/files/{id}`; stop defaulting missing `indexing_status` to “Indexing…”.
- **Non-goals:** Raise 1MB upload cap / nginx body size; OCR for scanned PDFs; merge chat into agent; dump file vectors into `notes_chunks`; add `indexing_status` column; `ChatRequest.file_id`.
