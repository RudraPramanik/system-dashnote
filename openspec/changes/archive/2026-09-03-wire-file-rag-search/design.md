## Context

See proposal.md for why Chat ignores indexed PDFs. Constraints: `WorkspaceVectorSearch` is the only Qdrant search interface; `FileVectorIndexer` already writes `files_chunks` with `file_id`, `workspace_id`, `created_by`, `visibility`; `build_rbac_filter()` already matches notes/files visibility; chat ≠ agent; no `workspace_id` / `file_id` on `/ai/*` bodies; DashNotes is outside this repo’s edit root.

Live evidence (2026-09-03): PDF `2c13e530-…` extracted 34,913 chars and upserted 48 points to `files_chunks`; `generate_file_metadata` failed on `{\n{` JSON; UI stayed on “Indexing…”.

## Goals / Non-Goals

**Goals:**
- Dual-collection search inside the existing wrapper (one query embedding, two filtered queries, merge by score).
- Citation and test-search payloads that name files without a new chat route.
- File detail JSON that exposes worker columns already on `files`.
- JSON salvage that recovers the observed extra-brace metadata payload.

**Non-Goals:**
- Changing collection names, embedding dim, or ingest/index worker topology.
- OCR, upload size, nginx `client_max_body_size`.
- Adding `indexing_status` to the schema or Alembic.
- Implementing DashNotes UI (document the contract in `frontendguide.md` only).

## Decisions

1. **Search both collections in `WorkspaceVectorSearch`, do not merge vectors into `notes_chunks`**  
   Slice 7 split collections on purpose (delete/reindex isolation). Slice 8 was “extend the search wrapper.”  
   Alternative: upsert files into `notes_chunks` with `source_type` in payload — rejected; mixes delete keys (`note_id` vs `file_id`) and violates existing indexer law.

2. **One query vector, two `query_points`, merge-sort by score, cap at `limit`**  
   Same `score_threshold` and `build_rbac_filter()` on both. Map file payloads with `source_type="file"`, `file_id=payload["file_id"]`, `note_id=""`. Map notes with `source_type="note"`, `file_id=""`.  
   Alternative: Qdrant hybrid/union API — not used elsewhere; extra dependency. Alternative: second search class — rejected; routers would bypass the single interface.

3. **Keep `search_notes` tool name; expand description + agent system prompt**  
   RagService.answer already becomes dual-collection; the tool stays one call. Avoid a second `search_files` tool (double retrieve, extra iteration).  
   Alternative: rename to `search_workspace` — cosmetic break for traces; skip.

4. **Citation: additive `source_type` + `file_id`; keep `note_id`**  
   OpenAPI-compatible for old clients that ignore unknown fields. File hits use empty `note_id` plus `file_id`. Grounding still matches `cited_chunk_ids` to retrieved chunks. Empty fallback copy in `RagService` and `RAG_SYSTEM_INSTRUCTION` says “notes and files”.  
   Alternative: overload `note_id` with file UUIDs — DashNotes would 404 on `/notes/{uuid}`.

5. **FileResponse: `summary`, `tags` always; `extracted_text` on GET-by-id only, truncated (8000 chars)**  
   Columns exist (`files.models`). List nulls `extracted_text` to avoid 500k-char list rows. No migration.  
   Alternative: new FileDetail schema — more OpenAPI churn for one field.

6. **JSON salvage: nested/extra `{` before a valid object**  
   Extend `extract_json_blob` (or a second pass) so `{\n{ "summary": ...}` yields the inner object. Metadata failure MUST NOT delete file vectors (already true).  
   Alternative: retry metadata on next fallback model only — still need salvage; do salvage first.

7. **Process ownership**  
   Search: API process via wrapper (chat, agent tools, test-search). Index writes: worker unchanged. File JSON: API `files/router.py`. Parse: `shared/llm/structured.py` used by worker `generate_file_metadata`.

## Risks / Trade-offs

- **[Risk] Dual query doubles Qdrant RTT** → Mitigation: reuse one embedding; both queries share filter/limit; typical `limit` ≤ 12.
- **[Risk] File collection missing** → Mitigation: `ensure_files_collection()` already used on upsert; call it before file query; empty collection ⇒ no file hits, notes still work.
- **[Risk] DashNotes still badges “Indexing…” and links file cites to notes** → Mitigation: `frontendguide.md` + OpenAPI; sibling client regen is required for UX, not for RAG answers.
- **[Risk] Salvage too aggressive parses wrong JSON** → Mitigation: still `model_validate` against `FileMetadataAnalysis`; invalid types fail as today.
- **[Risk] Score mix across collections** → Mitigation: same embed model and cosine threshold; merge by score only.

## Migration Plan

1. Ship API + worker image with wrapper/citation/FileResponse/salvage.
2. Recreate `api` (and `worker` if structured.py changed). Existing `files_chunks` points need no re-embed.
3. Clients regenerate OpenAPI types; until then extra JSON fields are ignored and RAG answers still improve.
4. Rollback: revert wrapper to notes-only; file vectors remain; chat behaves as today.

## Open Questions

None that block implementation. Sibling DashNotes apply is a separate change after this OpenAPI ships.
