## Purpose

Production-level AI/RAG/agent interview Q&A at `docs/documentation/qs2.md` for concept clearance and hire-loop answers, complementary to the repo-specific `qs.md`.

## ADDED Requirements

### Requirement: Interview Q&A document exists as a concept-clearance gate
The repository SHALL provide a production AI engineering interview Q&A document at `docs/documentation/qs2.md` that a candidate can use both to pass hiring loops and to verify they understand production RAG/agent systems.

#### Scenario: File is present, navigable, and non-empty
- **WHEN** a reader opens `docs/documentation/qs2.md`
- **THEN** the file MUST contain a title, a short purpose statement, a table of contents, and substantive Q&A sections
- **AND** the document MUST state that length is expected and that completeness is preferred over brevity

#### Scenario: Dual use as interview and concept gate
- **WHEN** a reader studies a question
- **THEN** the answer MUST be usable as a spoken interview response
- **AND** the same answer MUST include enough mechanism, tradeoff, and failure-mode depth to survive a follow-up “how would you actually do that?” probe

### Requirement: qs2 is complementary to qs.md, not a rewrite
`qs2.md` SHALL cover general production AI/RAG/agent engineering. `qs.md` SHALL remain the DashNoteSystem-specific talk track. The two documents MUST stay separate and MUST cross-link.

#### Scenario: Reader finds both tracks
- **WHEN** a reader opens `qs.md` or `qs2.md`
- **THEN** they MUST be able to follow a link or explicit pointer to the other file
- **AND** `qs2.md` MUST NOT replace or merge the DashNoteSystem-specific Q&A in `qs.md`

#### Scenario: Repo examples are labeled as examples
- **WHEN** an answer uses DashNoteSystem (or any single product) as an illustration
- **THEN** the answer MUST remain generally applicable to enterprise AI systems
- **AND** the illustration MUST be labeled as an example, not as the only valid architecture

### Requirement: Interview Q&A format is consistent and practiceable
Each Q&A block SHALL present a question a hiring manager or interviewer would ask, followed by an answer a candidate can practice out loud. The document MUST include a table of contents that maps to the major sections.

#### Scenario: Practice format is explicit
- **WHEN** a reader starts the document
- **THEN** they MUST see the intended practice format (question then answer)
- **AND** they MUST be able to jump to a topic from the table of contents

#### Scenario: Follow-up / counter-question coverage exists
- **WHEN** a reader prepares for interviewer pushback
- **THEN** the document MUST include a dedicated section of counter-questions or “why not X?” follow-ups covering at least RAG vs fine-tuning, chat vs agent, and vector DB vs querying the existing SQL database

### Requirement: Production RAG and enterprise integration coverage
The document SHALL explain how to add RAG to an existing enterprise system or existing database, including indexing strategy, sync, access control, and what not to do (dump the whole DB into a vector store blindly).

#### Scenario: Existing-database RAG question is answered
- **WHEN** an interviewer asks how to do RAG against an existing enterprise system or existing database
- **THEN** the document MUST describe a production approach covering source-of-truth data, chunking/indexing, incremental sync, and permission-aware retrieval
- **AND** it MUST warn against treating the vector index as a replacement for transactional queries

#### Scenario: Retrieval quality levers are covered
- **WHEN** an interviewer asks how to improve RAG quality
- **THEN** the document MUST cover at least chunking, embeddings, hybrid search, reranking, query rewriting, metadata filters, and evaluation of retrieval vs generation

### Requirement: Latency, cost, and agent-vs-RAG design coverage
The document SHALL explain how to reduce RAG and agent latency and how to choose between single-shot RAG and multi-step agents in production.

#### Scenario: Latency improvement question is answered
- **WHEN** an interviewer asks how to improve RAG or agent latency
- **THEN** the document MUST cover at least streaming, smaller/faster models for easy paths, caching, parallel retrieval, fewer agent hops, and avoiding unnecessary tool loops
- **AND** it MUST distinguish time-to-first-token from end-to-end latency

#### Scenario: Chat vs agent is an explicit design choice
- **WHEN** an interviewer asks when to use RAG chat versus an agent
- **THEN** the document MUST state that both can coexist
- **AND** it MUST give decision criteria (latency, tool needs, write actions, HITL) rather than “always use an agent”

### Requirement: Production operations, security, and evals coverage
The document SHALL cover production concerns interviewers treat as hire/no-hire: tenancy and RBAC in retrieval, prompt injection and data leakage, observability, evaluation, failure modes, and cost control.

#### Scenario: Security and tenancy answers exist
- **WHEN** an interviewer asks how RAG stays tenant-safe
- **THEN** the document MUST require that retrieval filters come from authenticated identity, not from the user prompt
- **AND** it MUST address prompt injection, tool-calling blast radius, and citation or grounding expectations

#### Scenario: Evals and failure modes are interview-ready
- **WHEN** an interviewer asks how you know the system works in production
- **THEN** the document MUST cover golden evals, online traces, empty-retrieval behavior, provider outages, embedding lag, and cost/latency measurement
- **AND** it MUST NOT claim a system is production-ready solely because a demo chat works
