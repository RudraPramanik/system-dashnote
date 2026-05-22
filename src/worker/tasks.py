"""
ARQ task registry — all background tasks listed here.

Slice 1: embed_note_task
Slice 2: index_chunks_task, delete_note_vectors_task  (TODO)
Slice 7: handle_file_uploaded, handle_note_created    (TODO)
"""
from worker.ingestion.tasks import embed_note_task

__all__ = ["embed_note_task"]
