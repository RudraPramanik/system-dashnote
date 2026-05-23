"""
ARQ task registry — all background tasks listed here.

Slice 1: embed_note_task
Slice 2: Qdrant upsert/delete inside embed_note_task (NoteVectorIndexer)
Slice 7: handle_file_uploaded, handle_note_created    (TODO)
"""
from worker.ingestion.tasks import embed_note_task

__all__ = ["embed_note_task"]
