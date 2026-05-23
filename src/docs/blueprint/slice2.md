# Slice 2 — Retrieve
## Final Cursor Prompts (Gemini Embeddings, Multi-Tenant, Production-Safe)

> **Context from Slice 1 (already built)**
> - Embedding model: `gemini/gemini-embedding-2` → **3072 dimensions**
> - Pipeline lives at: `src/ai/workflows/pipeline.py`
> - Chunker lives at: `src/ai/embeddings/chunker.py`
> - Cache lives at: `src/ai/services/cache.py`
> - Worker task: `src/worker/ingestion/tasks.py` → `embed_note_task`
> - `EmbeddedChunk` produced by pipeline — ready for Qdrant upsert
> - Import as: `from config import settings` (not `from src.config`)
> - Module path style: `from ai.embeddings.base import ...` (not `src.ai.`)
> - Slice 1 gate: `qdrant_indexed: false` in worker logs ✅

---

## ARCHITECTURE LAW
### Paste as your FIRST message in every new Cursor Composer session.

```
ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

MODULE PATHS (Docker image has /app/src on PYTHONPATH):
  Import as:  from config import settings
              from ai.embeddings.base import EmbeddedChunk
              from ai.workflows.pipeline import EmbeddingPipeline
              from shared.contracts.indexing import IndexingRequest
  NEVER as:   from src.config import ...
              from src.ai.embeddings import ...

AI MODULE IMPORT LAW — src/ai/* may ONLY import from:
  - config (settings)
  - ai.*
  - shared.*
  - stdlib + third-party packages
  NEVER: FastAPI, Request, Response, HTTPException, APIRouter, Depends
  NEVER: SQLAlchemy sessions or any repository class
  NEVER: notes.*, files.*, auth.*, workspaces.*
  NEVER: worker.*

WORKER IMPORT LAW — src/worker/* may ONLY import from:
  - config, ai.*, shared.*
  NEVER: FastAPI, HTTP objects, domain repositories, Qdrant in task files directly
         (Qdrant client lives in ai/retrieval/ — worker imports from there)

ROUTER LAW:
  - Do not refactor, reorder, or rewrite existing router logic
  - Append only — new routes go at the bottom of the file
  - Test search route mounts at /ai/test-search NOT /notes/test-search

INFRA LAW:
  - No new Dockerfiles or compose files
  - All changes go into existing Dockerfile and requirements.txt
  - Append-only to settings, .env, docker-compose.yml

QDRANT SECURITY LAW:
  - workspace_id MUST be a `must` filter on EVERY Qdrant query — no exceptions
  - workspace_id is ALWAYS injected from RequestContext — NEVER from user input
  - All Qdrant access goes through WorkspaceVectorSearch wrapper
  - Raw AsyncQdrantClient is NEVER called directly from routers or tasks

PYDANTIC LAW:
  - Pydantic V2 throughout
  - All shared models: ConfigDict(frozen=True)
  - Python 3.11+ type hints

EMBEDDING DIMENSION: 3072 (gemini/gemini-embedding-2)
COLLECTION NAME: notes_chunks

Acknowledge these laws before writing any code.
```

---

## Sub-step 2.1 — Qdrant Client + Collection Init + Write Path

**Goal:**
- `qdrant-client` installed
- Singleton `AsyncQdrantClient` created
- `notes_chunks` collection auto-provisioned on API startup with payload indexes
- Worker `embed_note_task` updated to actually upsert vectors
- Worker DELETE path wired to remove vectors by filter

**Gate:**
```powershell
# Create a note via API, then:
docker compose logs worker --tail 30
# Must show: qdrant_indexed: true

# Open Qdrant dashboard:
# http://127.0.0.1:6333/dashboard
# Must show: notes_chunks collection, vector size 3072, points > 0
# Click a point — payload must show workspace_id, note_id, created_by, visibility
```

**Files to open in Cursor:**
- `requirements.txt`
- `src/config/settings.py` (or `src/config.py` — wherever Settings lives)
- `src/main.py`
- `src/worker/ingestion/tasks.py`

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 2.1 — Install qdrant-client, create the Qdrant singleton
client, auto-provision the notes_chunks collection with payload indexes on
FastAPI lifespan startup, and wire real vector upsert + delete into the
existing embed_note_task ARQ worker.

CONTEXT:
- Embedding model: gemini/gemini-embedding-2 — vector dimension: 3072
- Collection name from settings: QDRANT_NOTES_COLLECTION = "notes_chunks"
- EmbeddedChunk objects are produced by EmbeddingPipeline in ai/workflows/pipeline.py
- embed_note_task in worker/ingestion/tasks.py currently logs qdrant_indexed: false
- Import style: from config import settings (NOT from src.config)
- Module style: from ai.retrieval.client import get_qdrant_client

LAWS IN EFFECT:
- Append-only to settings, .env, requirements.txt
- Qdrant singleton lives in ai/retrieval/client.py — nowhere else
- Worker imports Qdrant client from ai.retrieval.client — never instantiates it directly
- Do not touch chunker, cache, pipeline, or factory files from Slice 1
- Do not modify any existing notes router logic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — requirements.txt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read requirements.txt. Find the AI Slice 1 section.
Append immediately after it — do not duplicate if already present:

# --- AI Slice 2: Vector store ---
qdrant-client[async]>=1.9.1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Settings (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the Settings class. Append these fields if not already present.
Place them under a new comment after existing AI fields:

    # ── AI Slice 2: Qdrant ──────────────────────────────────────────
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_NOTES_COLLECTION: str = "notes_chunks"
    QDRANT_TIMEOUT: int = 30

Append computed property if not present:

    @property
    def qdrant_enabled(self) -> bool:
        """True when Qdrant URL is configured."""
        return bool(self.QDRANT_URL)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — .env (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Append at the bottom — skip any var already present:

# ── AI Slice 2 ──────────────────────────────────────────────────────
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
QDRANT_NOTES_COLLECTION=notes_chunks
QDRANT_TIMEOUT=30

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/ai/retrieval/client.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Qdrant async client singleton for DashNoteSystem.

ONE client instance per process — shared by the API and worker.
All Qdrant access in this project goes through get_qdrant_client().
Never instantiate AsyncQdrantClient elsewhere.

IMPORT LAW: Only qdrant_client, config, stdlib.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from qdrant_client import AsyncQdrantClient
from config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_qdrant_client() -> AsyncQdrantClient:
    """
    Return the process-wide Qdrant client singleton.
    lru_cache ensures a single connection is reused across all callers.
    Thread-safe for async — AsyncQdrantClient handles connection pooling.
    """
    settings = get_settings()
    client = AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        timeout=settings.QDRANT_TIMEOUT,
    )
    logger.info(
        "Qdrant client initialised",
        extra={"url": settings.QDRANT_URL},
    )
    return client

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — src/ai/retrieval/collections.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Qdrant collection provisioning for DashNoteSystem.

init_qdrant_schema() is called once at FastAPI lifespan startup.
It is idempotent — safe to call on every restart.

Collection: notes_chunks
Vector size: 3072 (gemini/gemini-embedding-2)
Distance: Cosine

Payload indexes (MANDATORY for multi-tenant performance):
  workspace_id, note_id, created_by, visibility
  Without these: every filter = full collection scan at O(n).
  With these: filter runs before ANN search — fast at any scale.

IMPORT LAW: Only qdrant_client, config, ai.retrieval.client, stdlib.
"""
from __future__ import annotations

import logging

from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
)

from config import get_settings
from ai.retrieval.client import get_qdrant_client

logger = logging.getLogger(__name__)

# Fields that MUST be indexed for tenant-safe filtering
_KEYWORD_INDEXES = ["workspace_id", "note_id", "created_by", "visibility"]


async def init_qdrant_schema() -> None:
    """
    Ensure notes_chunks collection and payload indexes exist.

    Called from FastAPI lifespan startup. Idempotent.
    Collection creation is skipped if it already exists.
    Index creation uses try/except per field — existing indexes are skipped.
    """
    settings = get_settings()
    client = get_qdrant_client()
    collection_name = settings.QDRANT_NOTES_COLLECTION

    # Check if collection already exists
    existing = {
        c.name
        for c in (await client.get_collections()).collections
    }

    if collection_name not in existing:
        logger.info(
            "Creating Qdrant collection",
            extra={
                "collection": collection_name,
                "dimension": settings.EMBEDDING_DIMENSION,
            },
        )
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,   # 3072 for gemini-embedding-2
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Qdrant collection created",
            extra={"collection": collection_name},
        )
    else:
        logger.debug(
            "Qdrant collection already exists — skipping create",
            extra={"collection": collection_name},
        )

    # Create payload indexes — idempotent, safe to re-run
    for field_name in _KEYWORD_INDEXES:
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.debug(
                "Payload index ensured",
                extra={"collection": collection_name, "field": field_name},
            )
        except Exception as e:
            # Index likely already exists — log and continue
            logger.debug(
                "Payload index already exists or skipped",
                extra={"field": field_name, "reason": str(e)},
            )

    logger.info(
        "Qdrant schema initialisation complete",
        extra={
            "collection": collection_name,
            "indexes": _KEYWORD_INDEXES,
        },
    )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 6 — src/main.py (append to lifespan startup only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the existing lifespan context manager in src/main.py carefully.
Find the startup block (before the yield).
Append ONLY this block after existing startup logic:

    # --- AI Slice 2: Qdrant schema init ---
    if settings.qdrant_enabled:
        try:
            from ai.retrieval.collections import init_qdrant_schema
            await init_qdrant_schema()
            logger.info("Qdrant schema ready")
        except Exception as e:
            # Non-fatal on startup — API continues without vector search
            logger.error("Qdrant schema init failed", extra={"error": str(e)})

Do NOT touch the shutdown block, router registrations, middleware,
or any other existing lifespan logic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 7 — src/worker/ingestion/tasks.py (update embed_note_task only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/worker/ingestion/tasks.py carefully.
Find embed_note_task. It currently logs qdrant_indexed=False.

UPDATE the UPSERT path only — replace the section that says
"Vectors are logged but NOT written to Qdrant yet" with real upsert logic.
Do not change function signature, error handling, or DELETE path structure.

Replace the log-only vector section with:

        # --- AI Slice 2: upsert vectors to Qdrant ---
        from ai.retrieval.client import get_qdrant_client
        from qdrant_client.models import PointStruct

        qdrant = get_qdrant_client()
        points = []
        for chunk in result.embedded_chunks:
            points.append(PointStruct(
                id=chunk.chunk_id,          # deterministic uuid5 from Slice 1
                vector=chunk.vector,         # 3072-dim Gemini vector
                payload={
                    "workspace_id": chunk.workspace_id,
                    "note_id": chunk.note_id,
                    "created_by": chunk.created_by,
                    "visibility": "private" if chunk.is_private else "public",
                    "text": chunk.chunk_text,
                    "chunk_index": chunk.chunk_index,
                    "title": request.title,
                    "char_start": chunk.metadata.get("char_start", 0),
                    "char_end": chunk.metadata.get("char_end", 0),
                },
            ))

        if points:
            await qdrant.upsert(
                collection_name=settings.QDRANT_NOTES_COLLECTION,
                points=points,
            )

Then update the final log statement — flip qdrant_indexed from False to True:

        logger.info(
            "embed_note_task complete",
            extra={
                "note_id": request.note_id,
                "workspace_id": request.workspace_id,
                "chunks_processed": result.chunks_processed,
                "chunks_from_cache": result.chunks_from_cache,
                "chunks_embedded": result.chunks_embedded,
                "total_tokens": result.total_tokens,
                "latency_ms": latency_ms,
                "qdrant_indexed": True,      # ← changed from False
                "points_upserted": len(points),
            },
        )

UPDATE the DELETE path — replace the placeholder log with real deletion:

        # --- AI Slice 2: delete vectors from Qdrant ---
        from ai.retrieval.client import get_qdrant_client
        from qdrant_client.models import FilterSelector, Filter, FieldCondition, MatchValue

        qdrant = get_qdrant_client()
        await qdrant.delete(
            collection_name=settings.QDRANT_NOTES_COLLECTION,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="note_id",
                            match=MatchValue(value=request.note_id),
                        ),
                        FieldCondition(
                            key="workspace_id",
                            match=MatchValue(value=request.workspace_id),
                        ),
                    ]
                )
            ),
        )
        logger.info(
            "Note vectors deleted from Qdrant",
            extra={
                "note_id": request.note_id,
                "workspace_id": request.workspace_id,
            },
        )

RULES:
- Do not change function signature or IndexingRequest parsing
- Do not change EmbeddingPipeline instantiation
- Do not remove existing error handling try/except blocks
- workspace_id MUST appear in the delete filter — never delete by note_id alone
- Always upsert — never insert (idempotent on retry)
- Show me the exact updated sections, not the full file unless it is under 80 lines

OUTPUT FORMAT:
For each task show:
  === FILE: <path> ===
  === ACTION: <create|append|update section> ===
  <exact code>
```

**Validation:**
```powershell
docker compose up -d --build api worker

# 1. Verify collection created on startup:
curl.exe -sS http://127.0.0.1:6333/collections/notes_chunks
# Expected: {"result":{"status":"green","vectors_count":0,...}}

# 2. Create a note via API, then check worker:
docker compose logs worker --tail 30
# Expected: qdrant_indexed: true, points_upserted > 0

# 3. Check Qdrant dashboard:
# http://127.0.0.1:6333/dashboard
# notes_chunks collection → vectors > 0
# Click any point → payload shows workspace_id, note_id, visibility

# 4. Delete the note, check worker:
docker compose logs worker --tail 20
# Expected: "Note vectors deleted from Qdrant" with note_id + workspace_id

# 5. API health still green:
curl.exe -sS http://127.0.0.1/health
```

**Commit:**
```bash
git commit -am "feat(slice2.1): qdrant client, collection init, worker upsert and delete"
```

---

## Sub-step 2.2 — RBAC Filters + Search Wrapper + Test Endpoint

**Goal:**
- `build_rbac_filter()` — tenant-safe filter that mirrors `notes/permissions.py` exactly
- `WorkspaceVectorSearch` — the ONLY interface to Qdrant search (raw client never called from routers)
- `GET /ai/test-search` — internal quality gate endpoint
- Slice 2 quality gate validated: relevance score > 0.4, workspace isolation confirmed

**Gate:**
```powershell
# Workspace A token — search your notes:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/test-search?q=your+note+topic&limit=3" `
  -Headers @{ Authorization = "Bearer <WORKSPACE_A_TOKEN>" }
# Expected: results with score > 0.4, all workspace_id = Workspace A

# Workspace B token — same query:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/test-search?q=your+note+topic&limit=3" `
  -Headers @{ Authorization = "Bearer <WORKSPACE_B_TOKEN>" }
# Expected: EMPTY array or only Workspace B results
# NEVER: Workspace A results in Workspace B response
```

**Files to open in Cursor:**
- `src/ai/retrieval/filters.py` (create empty)
- `src/ai/retrieval/wrapper.py` (create empty)
- `src/ai_routes/search.py` (create empty — new file)
- `src/main.py` (reference — to register the new router)
- `src/notes/permissions.py` (reference — RBAC logic to mirror)
- `src/core/security/context.py` (reference — RequestContext fields)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 2.2 — Build the RBAC security filter module, the
tenant-safe search wrapper, and mount the internal test search endpoint.

CONTEXT:
- RequestContext fields: user_id, workspace_id, role (from core/security/context.py)
- Role values: "owner", "admin", "member" (from notes/permissions.py)
- notes/permissions.py RBAC logic:
    owner/admin → can see ALL notes in workspace
    member → can see: own notes (created_by == user_id) OR public notes (is_private=False)
- Qdrant payload fields: workspace_id, note_id, created_by, visibility ("public"|"private")
- visibility field: "public" = is_private False, "private" = is_private True
- Embedding model: gemini/gemini-embedding-2 → 3072 dimensions
- Import style: from config import settings, from ai.retrieval.client import get_qdrant_client
- Collection: settings.QDRANT_NOTES_COLLECTION

LAWS IN EFFECT:
- workspace_id MUST be a `must` filter on every Qdrant query — NEVER optional
- workspace_id injected from RequestContext — NEVER from query parameters
- All Qdrant search goes through WorkspaceVectorSearch — raw client never in routers
- filters.py and wrapper.py import NO FastAPI, NO SQLAlchemy, NO repositories
- Test endpoint mounts at /ai/test-search — NOT /notes/test-search
- Do not touch notes/router.py — new router is src/ai_routes/search.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/ai/retrieval/filters.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
RBAC filter builder for Qdrant vector search.

build_rbac_filter() produces a Qdrant Filter that mirrors the RBAC
rules in src/notes/permissions.py EXACTLY.

Rules (must stay in sync with notes/permissions.py):
  owner / admin → see all notes in workspace
  member        → see own notes (created_by match) OR public notes (visibility=public)

Security contract:
  workspace_id is ALWAYS a `must` condition — never optional.
  It is injected from RequestContext (JWT wid claim) — never from user input.
  Cross-tenant data leakage is prevented at this layer.

IMPORT LAW: Only qdrant_client.models, stdlib.
No FastAPI. No SQLAlchemy. No config. No RequestContext import here —
ctx fields are passed as plain strings to keep this module pure.
"""
from __future__ import annotations

from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
)


def build_rbac_filter(
    workspace_id: str,
    user_id: str,
    role: str,
) -> Filter:
    """
    Build a Qdrant Filter enforcing workspace isolation and RBAC.

    Args:
        workspace_id: From RequestContext.workspace_id (JWT wid claim).
                      ALWAYS injected server-side — never from user input.
        user_id:      From RequestContext.user_id (JWT sub claim).
        role:         From RequestContext.role — "owner", "admin", or "member".

    Returns:
        Qdrant Filter ready to pass to client.search() query_filter parameter.

    Security:
        workspace_id is a `must` condition on every path.
        A developer CANNOT call this function without providing workspace_id.
    """
    # workspace_id is mandatory on EVERY query — no exceptions
    workspace_condition = FieldCondition(
        key="workspace_id",
        match=MatchValue(value=workspace_id),
    )

    if role in ("owner", "admin"):
        # Privileged roles see all notes in their workspace
        return Filter(must=[workspace_condition])

    # Member: can see own notes OR public notes
    # Mirrors notes/permissions.py member visibility rules exactly
    return Filter(
        must=[workspace_condition],
        should=[
            FieldCondition(
                key="visibility",
                match=MatchValue(value="public"),
            ),
            FieldCondition(
                key="created_by",
                match=MatchValue(value=user_id),
            ),
        ],
        minimum_should_match=1,
    )


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai/retrieval/wrapper.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Tenant-safe Qdrant search wrapper for DashNoteSystem.

WorkspaceVectorSearch is the ONLY interface to Qdrant search in this project.
Raw AsyncQdrantClient.search() is NEVER called from routers or services directly.

Why?
The wrapper guarantees workspace_id is always injected from RequestContext.
A developer cannot accidentally perform a cross-tenant search — it is
architecturally impossible without bypassing this class.

IMPORT LAW: Only qdrant_client, ai.retrieval.*, ai.embeddings.*, config, stdlib.
No FastAPI. No SQLAlchemy. No domain repositories.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client.models import ScoredPoint

from ai.retrieval.client import get_qdrant_client
from ai.retrieval.filters import build_rbac_filter
from ai.embeddings.factory import get_embedding_provider
from config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A single result from vector search — safe to return to any layer."""
    chunk_id: str
    note_id: str
    workspace_id: str
    created_by: str
    visibility: str
    chunk_text: str
    title: str
    chunk_index: int
    score: float


class WorkspaceVectorSearch:
    """
    Tenant-safe semantic search over the notes_chunks collection.

    Instantiate once and reuse — stateless between calls.
    All search calls require workspace_id, user_id, and role
    which are always sourced from RequestContext (JWT claims).

    Usage:
        searcher = WorkspaceVectorSearch()
        results = await searcher.search(
            query_text="project deadline",
            workspace_id=str(ctx.workspace_id),
            user_id=str(ctx.user_id),
            role=ctx.role,
            limit=5,
        )
    """

    async def search(
        self,
        *,
        query_text: str,
        workspace_id: str,
        user_id: str,
        role: str,
        limit: int = 10,
        score_threshold: float = 0.3,
    ) -> list[SearchResult]:
        """
        Perform hybrid-ready semantic search with RBAC enforcement.

        Args:
            query_text:      The user's search question.
            workspace_id:    From RequestContext — never user-supplied.
            user_id:         From RequestContext — never user-supplied.
            role:            From RequestContext — "owner", "admin", "member".
            limit:           Max results to return (1–50).
            score_threshold: Minimum cosine similarity to include (0–1).

        Returns:
            List of SearchResult ordered by relevance score descending.
            All results are guaranteed to belong to workspace_id.
        """
        settings = get_settings()

        # Step 1: embed the query using the same provider as ingestion
        # This ensures query and document vectors are in the same space
        provider = await get_embedding_provider()
        query_vector = await provider.embed_single(query_text)

        # Step 2: build RBAC filter — workspace_id always injected here
        rbac_filter = build_rbac_filter(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )

        # Step 3: execute vector search
        client = get_qdrant_client()
        raw_results: list[ScoredPoint] = await client.search(
            collection_name=settings.QDRANT_NOTES_COLLECTION,
            query_vector=query_vector,
            query_filter=rbac_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )

        logger.debug(
            "Vector search complete",
            extra={
                "workspace_id": workspace_id,
                "role": role,
                "query_length": len(query_text),
                "results_count": len(raw_results),
            },
        )

        # Step 4: map to SearchResult — extract payload safely
        results: list[SearchResult] = []
        for point in raw_results:
            p = point.payload or {}
            results.append(SearchResult(
                chunk_id=str(point.id),
                note_id=p.get("note_id", ""),
                workspace_id=p.get("workspace_id", ""),
                created_by=p.get("created_by", ""),
                visibility=p.get("visibility", "private"),
                chunk_text=p.get("text", ""),
                title=p.get("title", ""),
                chunk_index=p.get("chunk_index", 0),
                score=round(point.score, 4),
            ))

        return results


# Module-level singleton for reuse across requests
_searcher: WorkspaceVectorSearch | None = None


def get_workspace_vector_search() -> WorkspaceVectorSearch:
    """Return the process-wide WorkspaceVectorSearch singleton."""
    global _searcher
    if _searcher is None:
        _searcher = WorkspaceVectorSearch()
    return _searcher


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai_routes/__init__.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create empty module marker:
"""AI HTTP routes — mounted at /ai prefix in main.py."""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/ai_routes/search.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Internal AI search routes — DashNoteSystem.

GET /ai/test-search — semantic search validation endpoint.

This route is for engineering validation of retrieval quality.
It returns raw search results including scores for tuning purposes.
Gate before removing or restricting:
  - Cosine similarity scores consistently > 0.4 for relevant queries
  - workspace_id in every result matches the authenticated user's workspace
  - Different workspace JWTs return completely separate result sets

SECURITY: workspace_id is sourced from RequestContext (JWT wid claim) only.
          It is NEVER read from query parameters.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from core.security.dependency import get_current_context
from core.security.context import RequestContext
from ai.retrieval.wrapper import get_workspace_vector_search, SearchResult

router = APIRouter(prefix="/ai", tags=["ai-internal"])


@router.get(
    "/test-search",
    response_model=list[dict],
    summary="Internal: validate semantic search quality",
    description=(
        "Engineering validation endpoint. "
        "Returns raw vector search results with scores. "
        "workspace_id is always from JWT — never from query params."
    ),
)
async def test_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(default=5, ge=1, le=20, description="Max results"),
    ctx: RequestContext = Depends(get_current_context),
) -> list[dict]:
    """
    Run semantic search against notes_chunks collection.

    Security:
        workspace_id sourced from JWT (ctx.workspace_id) — not from query.
        RBAC filter applied: member sees own + public only.
        Owner/admin sees all notes in their workspace.

    Quality gate thresholds:
        score > 0.5 = strong semantic match
        score 0.3–0.5 = moderate match
        score < 0.3 = filtered out (score_threshold in wrapper)
    """
    searcher = get_workspace_vector_search()

    results: list[SearchResult] = await searcher.search(
        query_text=q,
        workspace_id=str(ctx.workspace_id),   # always from JWT
        user_id=str(ctx.user_id),              # always from JWT
        role=ctx.role,
        limit=limit,
    )

    # Return as plain dicts for easy inspection during validation
    return [
        {
            "chunk_id": r.chunk_id,
            "note_id": r.note_id,
            "title": r.title,
            "chunk_text": r.chunk_text[:200],   # truncate for readability
            "score": r.score,
            "visibility": r.visibility,
            "chunk_index": r.chunk_index,
            # workspace_id included so isolation can be verified visually
            "workspace_id": r.workspace_id,
        }
        for r in results
    ]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — src/main.py (append router registration only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/main.py. Find where existing routers are registered
(the include_router calls for auth, notes, files, etc.).

Append ONE new router registration after the existing ones:

    # --- AI Slice 2: internal search validation ---
    from ai_routes.search import router as ai_search_router
    app.include_router(ai_search_router)

Do not touch any existing include_router calls.
Do not touch middleware, lifespan, or health check registration.

Show me the exact line and where it is inserted.

OUTPUT FORMAT:
For each task:
  === FILE: <path> ===
  === ACTION: create | append | insert after line N ===
  <complete file content or exact addition>

Generate all files completely with zero truncation.
```

**Validation — Slice 2 Quality Gate:**
```powershell
docker compose up -d --build api

# Step 1: Verify search endpoint exists
curl.exe -sS http://127.0.0.1/ai/test-search?q=test
# Expected: 401 Unauthorized (auth working, route exists)

# Step 2: Get a token and search
# (Use your existing auth flow to get a JWT)
Invoke-RestMethod `
  -Uri "http://127.0.0.1/ai/test-search?q=your+note+content&limit=5" `
  -Headers @{ Authorization = "Bearer <YOUR_TOKEN>" }

# PASS condition 1 — Relevance:
# Results have "score" > 0.4 for queries matching your note content
# "title" matches notes you actually created
# "chunk_text" contains relevant content

# PASS condition 2 — Tenant isolation:
# Get a second token from a different workspace
# Run the SAME query
# Response MUST be empty array OR contain ONLY that workspace's notes
# NEVER: results from the first workspace appearing

# PASS condition 3 — Member RBAC:
# Login as a member role user
# Private notes created by OTHER members must NOT appear
# Your own private notes MUST appear
# All public notes MUST appear

# Step 3: Tuning guide if scores are low
# score consistently < 0.3 → check EMBEDDING_DIMENSION matches 3072
# score consistently < 0.4 → decrease CHUNK_SIZE to 600-800, re-index notes
# results irrelevant → check title is being prepended in chunker
# empty results → check payload indexes exist in Qdrant dashboard
```

**Commit:**
```bash
git commit -am "feat(slice2.2): rbac filters, search wrapper, test-search endpoint — slice 2 complete"
```

---

## Slice 2 Complete — What Was Built

```
src/ai/retrieval/
  client.py          ← AsyncQdrantClient singleton (lru_cache)
  collections.py     ← init_qdrant_schema() — collection + payload indexes
  filters.py         ← build_rbac_filter() — mirrors notes/permissions.py
  wrapper.py         ← WorkspaceVectorSearch — only Qdrant search interface

src/ai_routes/
  __init__.py        ← module marker
  search.py          ← GET /ai/test-search (internal quality gate)

src/worker/ingestion/tasks.py   ← updated: real upsert + delete (qdrant_indexed: true)
src/main.py                     ← lifespan: init_qdrant_schema() on startup
                                ← router: ai_search_router registered
requirements.txt                ← qdrant-client[async] added
settings                        ← QDRANT_URL, QDRANT_API_KEY, collection, timeout
.env                            ← Qdrant vars appended
```

```
What is NOT in Slice 2 (belongs to later slices):
  ✗ POST /ai/chat endpoint
  ✗ LLM response generation
  ✗ Conversation threads or memory
  ✗ LangGraph or any workflow orchestration
  ✗ Streaming responses
  ✗ Citations in responses
```

---

## Retrieval Tuning Reference

If the quality gate fails, tune in this order:

| Symptom | Fix |
|---|---|
| Scores all < 0.3 | Check `EMBEDDING_DIMENSION=3072` matches Gemini model output |
| Scores 0.3–0.4, results somewhat relevant | Reduce `CHUNK_SIZE` to 700, re-index all notes |
| Results irrelevant | Verify chunker prepends `# {title}\n\n` — title context matters |
| Empty results for valid query | Check payload indexes in Qdrant dashboard |
| Workspace leak | Check `build_rbac_filter` — workspace_must must be in `must` not `should` |
| Member sees private notes | Check `visibility` field set correctly in upsert payload |
| `vector dimension mismatch` error | Collection was created with wrong size — `docker compose down -v qdrant` then restart |

---

> **Next:** Slice 3 — Chat MVP
> `POST /ai/chat` — embed query → search → assemble prompt → LLM response → citations.
> No streaming yet. No memory yet. Just a working AI answer grounded in your notes.
> LiteLLM handles the chat completion the same way it handles embeddings.