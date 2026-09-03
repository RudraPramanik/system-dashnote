## Purpose

Exposes file automation output (extracted text, summary, tags) on the files API and keeps background metadata generation from failing permanently on salvageable structured-LLM JSON so clients can see ingest progress without an `indexing_status` column.

## Requirements

### Requirement: File JSON includes automation fields
`FileResponse` MUST include `summary` (nullable string), `tags` (JSON list of strings, default empty), and `extracted_text` (nullable string). `GET /files/{file_id}` MUST populate `extracted_text` from the stored extraction when present, truncated to a documented maximum so a single file cannot blow the payload. List endpoints MAY set `extracted_text` to null while still returning `summary` and `tags`. No Alembic migration is required when these columns already exist on `files`.

#### Scenario: Detail after successful extraction
- **GIVEN** the worker has saved non-empty `extracted_text` for a file the caller can read
- **WHEN** the client calls `GET /files/{file_id}`
- **THEN** the JSON MUST include that text (truncated if longer than the cap)
- **AND** MUST include `summary` and `tags` as stored (null or empty if metadata has not succeeded)

#### Scenario: List stays compact
- **GIVEN** at least one file with long extracted text
- **WHEN** the client calls `GET /files/`
- **THEN** each item MUST still include `summary` and `tags`
- **AND** `extracted_text` MUST be null or omitted so list payloads stay small

### Requirement: File metadata parse survives salvageable JSON
When the automation worker generates file summary and tags, it MUST parse structured LLM output with JSON salvage. Salvageable malformations (markdown fences, preamble, extra opening braces wrapping a valid object) MUST NOT leave the job failed if a valid summary and tags object can be recovered. Unrecoverable output MAY fail the job for retry according to existing worker policy. Vector indexing of the file MUST NOT depend on metadata success.

#### Scenario: Extra brace around valid metadata object
- **GIVEN** extracted text exists and the LLM returns JSON with a recoverable extra `{` before a valid `summary`/`tags` object
- **WHEN** `generate_file_metadata` runs
- **THEN** `files.summary` and `files.tags` MUST be persisted
- **AND** file vectors already written MUST remain

#### Scenario: Metadata failure does not un-index the file
- **GIVEN** file chunks were already upserted to the files collection
- **WHEN** metadata generation fails with unrecoverable JSON
- **THEN** those vectors MUST remain available for retrieval
- **AND** `summary`/`tags` MAY stay empty until a later successful job
