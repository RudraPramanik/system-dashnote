## 1. Dual-collection search (API process)

- [ ] 1.1 Extend `SearchResult` with `source_type` (`note` | `file`) and `file_id`; map notes vs files payloads in `WorkspaceVectorSearch.search()`. Query `notes_chunks` and `files_chunks` with one embedding, the same `build_rbac_filter()`, then merge by score and cap at `limit`. Call `ensure_files_collection()` before the files query. Do not write file points into `notes_chunks`.
- [ ] 1.2 Add `tests/ai/test_workspace_vector_search.py`: mock two `query_points` results, assert merge order, `source_type`/`file_id` mapping, and that the RBAC filter is passed to both collections. Include a case that a member filter is used (no live Qdrant).

## 2. RAG citations, prompts, agent, test-search

- [ ] 2.1 Add `source_type` and `file_id` on `Citation` in `rag_service.py`; populate from `SearchResult` for both `answer()` and `stream_answer()`. Change empty-retrieval copy (and `RAG_SYSTEM_INSTRUCTION` refuse line) to “notes and files”.
- [ ] 2.2 Expand `search_notes` tool description and `WORKSPACE_ASSISTANT_PROMPT` so the agent searches indexed files as well as notes. Keep tool name `search_notes`. Do not add `file_id` to chat/agent request bodies.
- [ ] 2.3 Include `source_type` and `file_id` on `GET /ai/test-search` result dicts. Update `tests/ai/` (new or existing RAG/citation tests) so file hits produce `source_type=file` citations and note hits keep `source_type=note`.

## 3. File API fields

- [ ] 3.1 Add `summary`, `tags`, and `extracted_text` to `FileResponse`. Truncate `extracted_text` to 8000 chars on `GET /files/{file_id}`. On list/admin-list, set `extracted_text` to null. No Alembic.
- [ ] 3.2 Add `tests/files/test_file_response_fields.py` (or extend files tests) asserting detail vs list extracted_text behavior.

## 4. Metadata JSON salvage (shared + worker)

- [ ] 4.1 Extend `extract_json_blob` / `parse_structured_response` so `{\n{ "summary": "...", "tags": [] }` validates as `FileMetadataAnalysis`. Keep Pydantic validation as the gate.
- [ ] 4.2 Extend `tests/shared/test_llm_structured.py` with the extra-brace fixture from the 2026-09-03 worker log. Confirm unrecoverable JSON still raises `StructuredLLMParseError`.

## 5. Docs

- [ ] 5.1 Update `docs/documentation/ai.md`: RAG/agent search both collections; citations include `source_type`/`file_id`; empty fallback wording.
- [ ] 5.2 Update `docs/documentation/frontendguide.md`: file citation navigation; missing `indexing_status` is not a forever badge; file JSON `summary`/`tags`/`extracted_text`; RAG covers files without client-sent `file_id` on `/ai/*`.
