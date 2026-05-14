from core.security.context import RequestContext
from notes.models import Note


def can_manage_note(ctx: RequestContext, note: Note) -> bool:
    """
    RBAC rules:
    - owner/admin can manage any note in the workspace
    - member can only manage their own notes
    """

    if ctx.role in {"owner", "admin"}:
        return True
    return note.created_by == ctx.user_id


def can_view_note_fields(
    ctx: RequestContext, *, is_private: bool, created_by: int
) -> bool:
    """
    Same visibility rules as can_view_note, for dict/cached payloads (no ORM instance).
    """

    if ctx.role in {"owner", "admin"}:
        return True
    if not is_private:
        return True
    return created_by == ctx.user_id


def can_view_note(ctx: RequestContext, note: Note) -> bool:
    """
    Visibility rules:
    - owner/admin can view any note
    - member can view public notes and their own private notes
    """

    return can_view_note_fields(
        ctx, is_private=note.is_private, created_by=note.created_by
    )

