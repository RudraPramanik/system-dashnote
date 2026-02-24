from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    """
    Workspace-aware request context.

    We use integer IDs here to match the `User.id` and `Workspace.id` columns.
    """

    user_id: int
    workspace_id: int
    role: str
