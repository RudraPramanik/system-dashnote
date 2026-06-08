"""
Automation worker tasks for DashNoteSystem.

Task progression:
  handle_file_uploaded  → extract text → index vectors → generate metadata
  handle_note_created   → auto-tag note

Fan-out pattern:
  Each task does ONE job and enqueues the next task on success.
  This ensures retries are isolated — extract failure ≠ index failure.

Slice 7.1: stubs — log event receipt, no business logic yet
Slice 7.2: handle_file_uploaded gets extraction + DB persistence
Slice 7.3: fan-out to indexing + metadata generation + note tagging
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field as PydanticField

logger = logging.getLogger(__name__)


class FileMetadataAnalysis(BaseModel):
    """Structured output for file metadata generation."""

    summary: str = PydanticField(
        description="Concise, informative summary of the document content. 2-4 sentences."
    )
    tags: list[str] = PydanticField(
        description="Up to 5 lowercase keyword tags. Single words or short phrases."
    )


class NoteTagAnalysis(BaseModel):
    """Structured output for note auto-tagging."""

    tags: list[str] = PydanticField(
        description="Up to 5 lowercase keyword tags for the note. Single words or short phrases."
    )


async def handle_file_uploaded(ctx: dict, *, event_data: dict) -> None:
    """
    Step 1 of file automation: extract text from uploaded file binary.

    Flow:
      1. Parse event_data to get file_id, workspace_id, mime_type
      2. Load file metadata from DB to get storage path
      3. Download file binary from storage backend
      4. Extract text using FileParsingEngine
      5. Persist extracted_text to files table
      6. Enqueue fan-out tasks (added in Sub-step 7.3)
    """
    import uuid
    import asyncio
    import functools

    from shared.utils.parsers import FileParsingEngine
    from core.storage.client import get_storage
    from core.database.session import AsyncSessionLocal
    import sqlalchemy as sa

    # Parse event — model_dump(mode="json") flattens payload fields to top level (7.0)
    try:
        file_id = event_data.get("file_id")
        workspace_id = event_data.get("workspace_id")
        mime_type = event_data.get("mime_type", "text/plain")

        if not file_id or not workspace_id:
            logger.error(
                "handle_file_uploaded: missing file_id or workspace_id",
                extra={"event_data_keys": list(event_data.keys())},
            )
            return
    except Exception as e:
        logger.error("handle_file_uploaded: event_data parse failed", extra={"error": str(e)})
        return

    # Step 1: Load file record to get storage_key
    file_record = None
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            result = await db.execute(
                sa.select(File).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            file_record = result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "handle_file_uploaded: DB lookup failed",
                extra={"file_id": file_id, "error": str(e)},
            )
            return

    if file_record is None:
        logger.warning(
            "handle_file_uploaded: file not found",
            extra={"file_id": file_id, "workspace_id": workspace_id},
        )
        return

    # Step 2: Download file binary from storage
    try:
        storage = get_storage()
        file_bytes = await storage.download(file_record.storage_key)
    except Exception as e:
        logger.error(
            "handle_file_uploaded: storage download failed",
            extra={"file_id": file_id, "error": str(e)},
        )
        return

    # Step 3: Extract text (CPU-bound — run in executor)
    try:
        loop = asyncio.get_event_loop()
        extracted_text = await loop.run_in_executor(
            None,
            functools.partial(
                FileParsingEngine.extract_text,
                file_bytes,
                file_record.mime_type,
            ),
        )
    except Exception as e:
        logger.error(
            "handle_file_uploaded: text extraction failed",
            extra={"file_id": file_id, "mime_type": file_record.mime_type, "error": str(e)},
        )
        extracted_text = ""   # non-fatal — continue without text

    # Step 4: Persist extracted_text to DB
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            await db.execute(
                sa.update(File)
                .where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
                .values(extracted_text=extracted_text)
            )
            await db.commit()
            logger.info(
                "handle_file_uploaded: extracted_text saved",
                extra={
                    "file_id": file_id,
                    "chars_extracted": len(extracted_text),
                    "mime_type": mime_type,
                },
            )
        except Exception as e:
            logger.error(
                "handle_file_uploaded: DB update failed",
                extra={"file_id": file_id, "error": str(e)},
            )
            return

    # --- AI Slice 7.3: fan-out to indexing and metadata ---
    arq_pool = ctx.get("arq_pool")
    if arq_pool and extracted_text:
        try:
            await arq_pool.enqueue_job(
                "index_file_chunks",
                file_id=file_id,
                workspace_id=workspace_id,
                created_by=event_data.get("uploaded_by", ""),
                is_private=event_data.get("is_private", False),
            )
            await arq_pool.enqueue_job(
                "generate_file_metadata",
                file_id=file_id,
                workspace_id=workspace_id,
            )
            logger.info(
                "handle_file_uploaded: fan-out jobs enqueued",
                extra={"file_id": file_id},
            )
        except Exception as e:
            logger.error(
                "handle_file_uploaded: fan-out enqueue failed",
                extra={"error": str(e)},
            )


async def handle_note_created(ctx: dict, *, event_data: dict) -> None:
    """
    Triggered when a note is created.
    Full implementation added in Sub-step 7.3.
    """
    logger.info(
        "handle_note_created received",
        extra={
            "event_type": event_data.get("event_type"),
            "note_id": event_data.get("note_id"),
            "workspace_id": event_data.get("workspace_id"),
        },
    )
    # --- AI Slice 7.3: fan-out to note tagging ---
    from config import get_settings

    settings = get_settings()
    arq_pool = ctx.get("arq_pool")
    if arq_pool and settings.ai_enabled:
        try:
            await arq_pool.enqueue_job(
                "generate_note_tags",
                note_id=event_data.get("note_id"),
                workspace_id=event_data.get("workspace_id"),
                content=event_data.get("content", ""),
                title=event_data.get("title", ""),
            )
        except Exception as e:
            logger.error(
                "handle_note_created: fan-out enqueue failed",
                extra={"error": str(e)},
            )


async def handle_note_updated(ctx: dict, *, event_data: dict) -> None:
    """Triggered when note content changes. Stub for future use."""
    logger.info("handle_note_updated received", extra={"event_data": event_data})


async def handle_file_deleted(ctx: dict, *, event_data: dict) -> None:
    """Triggered when a file is deleted. Stub for Qdrant vector cleanup."""
    logger.info("handle_file_deleted received", extra={"event_data": event_data})
    # TODO: delete file vectors from QDRANT_FILES_COLLECTION


async def index_file_chunks(
    ctx: dict,
    *,
    file_id: str,
    workspace_id: str,
    created_by: str,
    is_private: bool,
) -> None:
    """
    Embed and index file extracted_text into QDRANT_FILES_COLLECTION.
    Reuses EmbeddingPipeline (Slice 1) + FileVectorIndexer (7.0) — no raw Qdrant in task.
    """
    import uuid

    import sqlalchemy as sa

    from ai.embeddings.factory import get_embedding_provider
    from ai.retrieval.indexer import FileVectorIndexer
    from ai.workflows.pipeline import EmbeddingPipeline
    from config import get_settings
    from core.database.session import AsyncSessionLocal

    settings = get_settings()
    if not settings.ai_enabled or not settings.qdrant_enabled:
        return

    file_name = "Untitled File"
    extracted_text = None
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File

            result = await db.execute(
                sa.select(File.extracted_text, File.name).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            row = result.first()
            if row:
                extracted_text = row.extracted_text
                file_name = row.name or file_name
        except Exception as e:
            logger.error("index_file_chunks: DB load failed", extra={"error": str(e)})
            return

    if not extracted_text or not extracted_text.strip():
        logger.info("index_file_chunks: no text to index", extra={"file_id": file_id})
        return

    try:
        provider = await get_embedding_provider()
        pipeline = EmbeddingPipeline(provider=provider, redis=ctx.get("redis"))
        result = await pipeline.process_note(
            note_id=file_id,
            workspace_id=workspace_id,
            created_by=created_by,
            is_private=is_private,
            title=file_name,
            content=extracted_text,
            metadata={"source_type": "file", "title": file_name},
        )
        if not result.embedded_chunks:
            return

        indexer = FileVectorIndexer(workspace_id)
        count = await indexer.index_file_chunks(file_id, result.embedded_chunks)
        logger.info(
            "index_file_chunks complete",
            extra={
                "file_id": file_id,
                "chunks_indexed": count,
                "collection": settings.QDRANT_FILES_COLLECTION,
            },
        )
    except Exception as e:
        logger.error(
            "index_file_chunks failed",
            extra={"file_id": file_id, "error": str(e)},
        )
        raise


async def generate_file_metadata(
    ctx: dict,
    *,
    file_id: str,
    workspace_id: str,
) -> None:
    """
    Generate AI summary and tags for a file using structured LLM output.
    Non-destructive — safe to retry. No governance check needed.
    Triggered by handle_file_uploaded fan-out.
    """
    import uuid

    import litellm
    import sqlalchemy as sa

    from config import get_settings
    from core.database.session import AsyncSessionLocal

    settings = get_settings()
    if not settings.ai_enabled:
        return

    async with AsyncSessionLocal() as db:
        try:
            from files.models import File

            result = await db.execute(
                sa.select(File.extracted_text).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            row = result.first()
            extracted_text = row.extracted_text if row else None
        except Exception as e:
            logger.error(
                "generate_file_metadata: DB load failed",
                extra={"error": str(e)},
            )
            return

    if not extracted_text or not extracted_text.strip():
        logger.info("generate_file_metadata: no text", extra={"file_id": file_id})
        return

    context_text = extracted_text[:6000]

    try:
        response = await litellm.acompletion(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a document analyst. Generate a concise summary and "
                        "relevant keyword tags for the provided document content. "
                        "Base everything strictly on the provided text. No external knowledge."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Document content:\n\n{context_text}\n\nGenerate summary and tags.",
                },
            ],
            response_format=FileMetadataAnalysis,
            temperature=0.0,
            max_tokens=512,
        )
        parsed = FileMetadataAnalysis.model_validate_json(
            response.choices[0].message.content
        )
    except Exception as e:
        logger.error(
            "generate_file_metadata: LLM call failed",
            extra={"error": str(e)},
        )
        return

    async with AsyncSessionLocal() as db:
        try:
            from files.models import File

            await db.execute(
                sa.update(File)
                .where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
                .values(summary=parsed.summary, tags=parsed.tags)
            )
            await db.commit()
            logger.info(
                "generate_file_metadata complete",
                extra={"file_id": file_id, "tags": parsed.tags},
            )
        except Exception as e:
            logger.error(
                "generate_file_metadata: DB update failed",
                extra={"error": str(e)},
            )


async def generate_note_tags(
    ctx: dict,
    *,
    note_id: str,
    workspace_id: str,
    content: str,
    title: str,
) -> None:
    """
    Auto-tag a note using structured LLM output.
    Non-destructive — safe to retry. No governance check needed.
    Triggered by handle_note_created fan-out.
    """
    import litellm
    import sqlalchemy as sa

    from config import get_settings
    from core.database.session import AsyncSessionLocal

    settings = get_settings()
    if not settings.ai_enabled:
        return

    context_text = f"Title: {title}\n\n{content[:3000]}"

    try:
        response = await litellm.acompletion(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate relevant keyword tags for the note. "
                        "Base tags strictly on content provided."
                    ),
                },
                {"role": "user", "content": context_text},
            ],
            response_format=NoteTagAnalysis,
            temperature=0.0,
            max_tokens=128,
        )
        parsed = NoteTagAnalysis.model_validate_json(
            response.choices[0].message.content
        )
    except Exception as e:
        logger.error("generate_note_tags: LLM call failed", extra={"error": str(e)})
        return

    async with AsyncSessionLocal() as db:
        try:
            from notes.models import Note

            await db.execute(
                sa.update(Note)
                .where(
                    Note.id == int(note_id),
                    Note.workspace_id == int(workspace_id),
                )
                .values(tags=parsed.tags)
            )
            await db.commit()
            logger.info(
                "generate_note_tags complete",
                extra={"note_id": note_id, "tags": parsed.tags},
            )
        except Exception as e:
            logger.error(
                "generate_note_tags: DB update failed",
                extra={"error": str(e)},
            )
