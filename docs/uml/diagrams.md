# DashNoteSystem UML Diagrams

Source: [`src/docs/lld.md`](../../src/docs/lld.md)

---

## 1. Protected HTTP request

Sequence for any JWT-protected route (notes, files, AI chat, etc.).

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant N as Nginx
    participant P as ProxyHeadersMiddleware
    participant RL as RateLimiter
    participant R as Redis
    participant O as oauth2_scheme
    participant D as get_current_context
    participant TS as TokenStore
    participant RT as Router
    participant PM as Permissions
    participant RP as Repository
    participant DB as PostgreSQL

    C->>N: HTTP + Authorization Bearer
    N->>P: Forward X-Forwarded-For, X-Request-ID
    P->>RL: enforce_global_rate_limit
    RL->>R: INCR rate_limit key
    alt limit exceeded
        RL-->>C: 429 Retry-After
    end
    RL->>O: extract token
    O->>D: decode JWT
    D->>TS: optional blacklist check jti
    D-->>RT: RequestContext sub wid role
    RT->>PM: require_roles / domain helper
    alt forbidden
        PM-->>C: 403
    end
    RT->>RP: query workspace_id scoped
    RP->>DB: tenant_filter + SQL
    DB-->>RP: rows
    RP-->>RT: models
    RT-->>C: Pydantic JSON response
```

---

## 2. Application layers

Component view of the backend layering (§6).

```mermaid
flowchart TB
    subgraph Edge["Edge"]
        NGINX[Nginx limit_req proxy]
    end

    subgraph App["App shell — main.py"]
        MW[Middleware CORS ProxyHeaders]
        RL[Global rate limit]
        RT[Routers auth notes files ai]
        MET[GET /metrics]
    end

    subgraph Security["core/security"]
        CTX[RequestContext JWT decode]
        RBAC[require_roles permissions]
    end

    subgraph Domain["Domain modules"]
        AUTH[auth]
        NOTES[notes notebooks]
        FILES[files]
        WS[workspaces membership]
    end

    subgraph AI["AI stack"]
        ROUTES[ai_routes ai_gateway]
        CORE[ai embeddings retrieval rag]
        SLLM[shared/llm retry structured]
        MEM[ai_memory ai/memory]
        AGENT[workflows tools checkpointer]
        WRK[worker ARQ automation]
    end

    subgraph Infra["Infrastructure"]
        PG[(PostgreSQL)]
        RD[(Redis)]
        QD[(Qdrant)]
        ST[StorageBackend local S3]
        OBS[observability Langfuse]
    end

    NGINX --> MW
    MW --> RL --> RT
    RT --> CTX --> RBAC
    RT --> Domain
    RT --> ROUTES
    ROUTES --> CORE
    ROUTES --> SLLM
    CORE --> MEM
    ROUTES --> AGENT
    AGENT --> SLLM
    WRK --> SLLM
    Domain --> PG
    Domain --> RD
    Domain --> ST
    CORE --> QD
    CORE --> RD
    WRK --> CORE
    WRK --> QD
    RT --> MET
    CORE --> OBS
```

---

## 3. Embedding pipeline (Slice 1)

Note content → chunks → cached embeddings.

```mermaid
sequenceDiagram
    autonumber
    participant API as notes/router
    participant ARQ as ARQ Redis queue
    participant W as embed_note_task
    participant P as EmbeddingPipeline
    participant CH as TextChunker
    participant CA as EmbeddingCache
    participant RD as Redis
    participant EP as LiteLLM Provider
    participant LF as LiteLLM API

    API->>ARQ: enqueue IndexingRequest
    ARQ->>W: dequeue job
    W->>P: process_note
    P->>CH: chunk_note title + content
    CH-->>P: list ChunkResult

    loop each chunk
        P->>CA: get_cached_vector text
        CA->>RD: GET embed:v1 sha256
        alt cache hit
            RD-->>P: vector
        else cache miss
            P->>EP: embed_texts batch
            EP->>LF: aembedding
            LF-->>EP: vectors
            EP-->>P: EmbeddingVector
            P->>CA: cache_vector
            CA->>RD: SETEX
        end
    end

    P-->>W: EmbeddedChunk list + metrics
```

---

## 4. ARQ worker indexing

Full worker path including Qdrant upsert (Slice 1 + 2).

```mermaid
sequenceDiagram
    autonumber
    participant W as embed_note_task
    participant P as EmbeddingPipeline
    participant I as NoteVectorIndexer
    participant Q as WorkspaceVectorIndex
    participant QD as Qdrant

    W->>W: validate IndexingRequest
    alt DELETE operation
        W->>I: delete_note
        I->>Q: delete by note_id
        Q->>QD: delete points
    else UPSERT
        W->>P: process_note
        P-->>W: EmbeddedChunk list
        W->>I: index_note_chunks
        I->>I: delete_note then upsert
        I->>Q: upsert points + payload
        Q->>QD: upsert workspace_id visibility created_by
    end
    W-->>W: IndexingResult log metrics
```

---

## 5. Semantic search + RBAC

`GET /ai/test-search` and internal retrieval used by RAG.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant RT as ai_gateway/search
    participant CTX as RequestContext
    participant WS as WorkspaceVectorSearch
    participant EP as EmbeddingProvider
    participant F as build_rbac_filter
    participant QD as Qdrant

    C->>RT: GET /ai/test-search q limit
    RT->>CTX: get_current_context JWT
    Note over RT,CTX: workspace_id never from query params
    RT->>WS: search q workspace_id user_id role
    WS->>EP: embed_single q
    EP-->>WS: query vector
    WS->>F: build_rbac_filter
    F-->>WS: Filter must workspace_id should visibility
    WS->>QD: query_points filter rbac limit
    QD-->>WS: scored payloads
    WS-->>RT: SearchResult list
    RT-->>C: JSON hits chunk_id score visibility
```

---

## 6. RAG chat (JSON)

`POST /ai/chat` with optional thread memory.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant RT as ai_routes/chat
    participant CTX as RequestContext
    participant RS as RagService
    participant TS as ThreadService
    participant CB as ContextBuilder
    participant WS as WorkspaceVectorSearch
    participant LLM as LiteLLM
    participant TR as ThreadRepository
    participant DB as PostgreSQL

    C->>RT: POST /ai/chat message thread_id
    RT->>CTX: JWT
    RT->>RT: freeze workspace_id user_id role
    RT->>RS: answer question thread_id db

    opt thread_id set
        RS->>TS: get_or_create_thread load history
        TS->>TR: workspace scoped queries
        TR->>DB: ai_threads ai_messages
    end

    RS->>WS: search RBAC
    WS-->>RS: retrieved chunks
    RS->>CB: build history + chunks budget
    CB-->>RS: messages array
    RS->>LLM: acompletion response_format RAGAnswer
    LLM-->>RS: answer cited_chunk_ids
    RS->>RS: ground citations to retrieved set

    opt db session
        RS->>TS: persist_turn
        TS->>TR: insert messages
    end

    RS-->>RT: ChatResult thread_id citations
    RT-->>C: ChatResponse JSON
```

---

## 7. RAG streaming (SSE)

`POST /ai/chat/stream` — same logic, progressive tokens.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant RT as ai_routes/chat
    participant RS as RagService
    participant LLM as LiteLLM stream

    C->>RT: POST /ai/chat/stream
    RT->>RT: freeze ctx before generate
    RT->>RS: stream_answer frozen strings

    RS->>RS: retrieve + ContextBuilder same as answer

    loop token stream
        RS->>LLM: acompletion stream True
        LLM-->>RS: delta
        RS-->>RT: StreamToken
        RT-->>C: SSE type token
    end

    RS-->>RT: StreamMetadata citations thread_id
    RT-->>C: SSE type metadata
    RT-->>C: data DONE

    Note over RT,C: Headers Cache-Control no-cache X-Accel-Buffering no
```

---

## 8. Conversation memory layers

Class collaboration — product layer vs agent execution layer.

```mermaid
classDiagram
    direction TB

    class RequestContext {
        +user_id str
        +workspace_id str
        +role str
    }

    class AIThread {
        +id UUID
        +workspace_id str
        +created_by str
        +is_active bool
    }

    class AIMessage {
        +id UUID
        +thread_id UUID
        +role str
        +content str
        +citations JSONB
    }

    class ThreadRepository {
        +list_threads(db, workspace_id, user_id)
        +get_recent_messages(...)
        +delete_thread(...) soft
    }

    class ThreadService {
        +get_or_create_thread(...)
        +load_history(...)
        +persist_turn(...)
    }

    class ContextBuilder {
        +build(question, history, chunks) BuiltContext
    }

    class RagService {
        +answer(...) ChatResult
        +stream_answer() StreamEvent
    }

    class AsyncPostgresSaver {
        <<LangGraph execution layer>>
        +checkpoints by thread_id string
    }

    AIThread "1" --> "*" AIMessage
    ThreadRepository --> AIThread
    ThreadRepository --> AIMessage
    ThreadService --> ThreadRepository
    RagService --> ThreadService
    RagService --> ContextBuilder
    RagService ..> RequestContext : plain strings only at boundary

    note for AsyncPostgresSaver "Linked to AIThread.id by thread_id string no FK"
```

---

## 9. LangGraph agent loop

State machine + invoke sequence for `POST /ai/agent`.

```mermaid
stateDiagram-v2
    [*] --> Agent: START
    Agent --> Tools: tool_calls present AND steps_taken less max
    Tools --> Agent: tool results
    Agent --> [*]: no tools OR max iterations
```

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant RT as ai_routes/agent
    participant G as workspace_assistant graph
    participant M as call_model acompletion_with_retry
    participant TN as tool_node
    participant T as StructuredTools
    participant RS as RagService
    participant NS as NoteService
    participant CP as AsyncPostgresSaver

    C->>RT: POST /ai/agent message thread_id
    RT->>RT: freeze ctx db_session_var.set
    RT->>G: ainvoke state config thread_id
    G->>CP: load checkpoint optional

    loop until END or AGENT_MAX_ITERATIONS
        G->>M: acompletion_with_retry tools function defs
        alt tool_calls
            M-->>G: assistant message + tools
            G->>TN: execute_tools
            alt search_notes summarize_workspace
                TN->>RS: answer workspace_id user_id role
            else create_note update_note
                TN->>NS: NoteService db from contextvar
            end
            TN-->>G: tool messages
        else final answer
            M-->>G: text response
        end
    end

    G->>CP: save checkpoint
    RT->>RT: db_session_var.reset
    alt LLM retries exhausted
        RT-->>C: 503 LLM temporarily unavailable
    else success
        RT-->>C: AgentResponse steps_taken tool_calls_made
    end
```

---

## 10. Docker Compose deployment

Runtime deployment view (see also `src/docs/system.md`).

```mermaid
flowchart LR
    subgraph Host["Host"]
        U[Client browser curl]
    end

    subgraph Compose["docker compose"]
        NG[nginx :80]
        API[api :8000]
        WRK[worker ARQ]
        PG[(db postgres :5432)]
        RD[(redis :6379)]
        QD[(qdrant :6333)]
        PR[prometheus :9090]
        GF[grafana :3001]
        MG[migrate one-shot]
    end

    U -->|HTTP 80| NG
    U -.->|debug 8000| API
    NG --> API
    API --> PG
    API --> RD
    API --> QD
    WRK --> PG
    WRK --> RD
    WRK --> QD
    PR -->|scrape /metrics| API
    GF --> PR
    MG --> PG

    note1[notes router enqueues embed jobs to Redis]
    API -.-> note1
    note1 -.-> WRK
```

---

## 11. Automation fan-out (Slice 7)

File upload and note create event pipelines through the ARQ worker.

```mermaid
sequenceDiagram
    autonumber
    participant API as files/notes router
    participant BUS as emit_event
    participant ARQ as ARQ Redis
    participant W as worker
    participant ST as StorageBackend
    participant PAR as FileParsingEngine
    participant DB as PostgreSQL
    participant LLM as acompletion_structured
    participant EP as EmbeddingPipeline
    participant QD as Qdrant

    alt FileUploadedEvent
        API->>BUS: FileUploadedEvent
        BUS->>ARQ: handle_file_uploaded
        ARQ->>W: dequeue
        W->>ST: download storage_key
        W->>PAR: extract_text mime
        PAR-->>W: extracted_text
        W->>DB: UPDATE files.extracted_text
        W->>ARQ: enqueue index_file_chunks
        W->>ARQ: enqueue generate_file_metadata
        ARQ->>W: index_file_chunks
        W->>EP: process_note file content
        W->>QD: FileVectorIndexer upsert files_chunks
        ARQ->>W: generate_file_metadata
        W->>LLM: FileMetadataAnalysis schema
        LLM-->>W: summary + tags
        W->>DB: UPDATE files.summary tags
    else NoteCreatedEvent
        API->>BUS: NoteCreatedEvent
        BUS->>ARQ: handle_note_created
        ARQ->>W: dequeue
        W->>ARQ: enqueue generate_note_tags
        ARQ->>W: generate_note_tags
        W->>LLM: NoteTagAnalysis schema
        LLM-->>W: tags
        W->>DB: UPDATE notes.tags
    end

    Note over W,LLM: Transient LLM failure re-raises for ARQ retry
```

---

## 12. Shared LLM layer (Slice 7.5)

Class collaboration for structured and retry-wrapped completions.

```mermaid
classDiagram
    direction TB

    class acompletion_structured {
        +messages list
        +schema BaseModel
        +max_tokens int
        +returns BaseModel
    }

    class acompletion_with_retry {
        +kwargs litellm params
        +returns ModelResponse
    }

    class parse_structured_response {
        +raw str
        +schema type
        +returns BaseModel
    }

    class extract_json_blob {
        +raw str
        +returns str JSON
    }

    class StructuredLLMParseError {
        <<ValueError>>
    }

    class RETRYABLE_EXCEPTIONS {
        RateLimitError
        Timeout
        ServiceUnavailableError
        APIConnectionError
    }

    class generate_note_tags {
        worker task
    }

    class generate_file_metadata {
        worker task
    }

    class AutomationDecisionEngine {
        evaluate_action
    }

    class call_model {
        workspace_assistant
    }

    acompletion_structured --> parse_structured_response
    parse_structured_response --> extract_json_blob
    parse_structured_response ..> StructuredLLMParseError : raises
    acompletion_structured ..> RETRYABLE_EXCEPTIONS : retries
    acompletion_with_retry ..> RETRYABLE_EXCEPTIONS : retries

    generate_note_tags --> acompletion_structured
    generate_file_metadata --> acompletion_structured
    AutomationDecisionEngine --> acompletion_structured
    call_model --> acompletion_with_retry

    note for acompletion_structured "Used by worker automation + governance"
    note for acompletion_with_retry "Used by agent call_model only"
```
