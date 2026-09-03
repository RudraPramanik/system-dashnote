## Purpose

Grounds Fast RAG chat and the workspace agent on indexed notes **and** uploaded files by searching both Qdrant collections under the same tenant and RBAC rules, without merging chat into agent or mixing file vectors into the notes collection.

## ADDED Requirements

### Requirement: Semantic search covers notes and files in the workspace
When AI is enabled and Qdrant is configured, workspace semantic search MUST retrieve relevant chunks from both the notes vector collection and the files vector collection. File chunks MUST remain stored in the files collection. Search MUST inject `workspace_id` from request context (JWT `wid`) and MUST apply the same role-based visibility filter used for notes: owner and admin see all workspace hits; member sees public plus own (`created_by`) private hits. Cross-tenant results MUST NOT appear.

#### Scenario: Indexed file is retrieved for a matching question
- **GIVEN** a file in the caller's workspace has extracted text embedded into the files collection
- **AND** the caller’s JWT `wid` matches that workspace
- **WHEN** the user asks a question whose meaning matches that file content via `POST /ai/chat` or `POST /ai/chat/stream`
- **THEN** retrieval MUST include at least one chunk from that file among the chunks considered for the answer
- **AND** the answer MUST NOT be the empty-notes fallback solely because no note chunks matched

#### Scenario: Notes still retrieve when files also exist
- **GIVEN** both a note and a file are indexed in the same workspace
- **WHEN** the user asks a question that matches the note more strongly than the file
- **THEN** the higher-scoring note chunks MUST still be eligible for the answer
- **AND** file chunks MUST still be eligible when their scores pass the same threshold

#### Scenario: Member cannot retrieve another member's private file
- **GIVEN** member A uploaded a private file that is indexed
- **WHEN** member B (same workspace, role member) asks a question that would match that file
- **THEN** retrieval MUST NOT return that file's chunks
- **AND** owner or admin in the same workspace MAY receive those chunks

#### Scenario: Other workspace JWT cannot retrieve the file
- **GIVEN** a file is indexed for workspace W1
- **WHEN** a valid JWT for workspace W2 calls chat or `GET /ai/test-search`
- **THEN** no chunk from that file MUST appear in results

### Requirement: Citations distinguish note and file sources
Citations returned from RAG (non-stream JSON and SSE `type: metadata`) MUST include `source_type` of `note` or `file`, plus `chunk_id`, `title`, and `relevance_score`. Note citations MUST include `note_id`. File citations MUST include `file_id`. The system MUST NOT invent citations that were not in the retrieved set. `GET /ai/test-search` MUST expose `source_type` and `file_id` when the hit is a file so engineering validation can see file retrieval.

#### Scenario: File-grounded chat metadata
- **GIVEN** retrieval used a file chunk to produce an answer
- **WHEN** `POST /ai/chat/stream` completes successfully
- **THEN** the `metadata` payload MUST include a citation with `source_type` `file` and that file's `file_id`
- **AND** MUST NOT require a real note id for that citation

#### Scenario: Note-grounded chat metadata unchanged in kind
- **GIVEN** retrieval used only note chunks
- **WHEN** chat returns citations
- **THEN** those citations MUST have `source_type` `note` and a `note_id`

#### Scenario: Diagnostic search shows file hits
- **GIVEN** an indexed file matches query text `q`
- **WHEN** an authenticated caller hits `GET /ai/test-search` with that `q`
- **THEN** at least one result MUST include `source_type` `file` and the file's `file_id` when that file outranks or joins note hits above the score threshold

### Requirement: Agent uses the same workspace retrieval as chat
The LangGraph workspace agent MUST be able to answer questions about indexed file content using the same tenant-safe retrieval as Fast RAG. Chat routes (`/ai/chat*`) and agent routes (`/ai/agent*`) MUST both remain. The client MUST NOT send `workspace_id` or `file_id` on those bodies to override JWT tenancy.

#### Scenario: Agent answers from an indexed file
- **GIVEN** a file is indexed in the caller's workspace
- **WHEN** the user asks the agent about that document's content via `POST /ai/agent` or `/ai/agent/stream`
- **THEN** the agent MUST be able to ground the answer on that file's retrieved chunks
- **AND** `/ai/chat` MUST still exist as a separate path

#### Scenario: Empty retrieval copy mentions files
- **GIVEN** no note or file chunks pass the relevance threshold
- **WHEN** chat or agent retrieval returns nothing
- **THEN** the user-visible fallback MUST state that nothing relevant was found in notes **and** files
- **AND** MUST NOT imply the product only searches notes

### Requirement: Chat and agent remain separate paths
File retrieval MUST apply to both `/ai/chat*` and `/ai/agent*` without replacing one with the other.

#### Scenario: Both surfaces remain
- **WHEN** this capability is enabled
- **THEN** `POST /ai/chat` and `POST /ai/chat/stream` still exist
- **AND** `POST /ai/agent` and `POST /ai/agent/stream` still exist
