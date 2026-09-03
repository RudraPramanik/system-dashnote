## ADDED Requirements

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
