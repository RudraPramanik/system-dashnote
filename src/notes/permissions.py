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


def can_view_note(ctx: RequestContext, note: Note) -> bool:
    """
    Visibility rules:
    - owner/admin can view any note
    - member can view public notes and their own private notes
    """

    if ctx.role in {"owner", "admin"}:
        return True
    if not note.is_private:
        return True
    return note.created_by == ctx.user_id

