"""
RBAC filter builder for Qdrant vector search.

build_rbac_filter() produces a Qdrant Filter that mirrors the RBAC
rules in src/notes/permissions.py EXACTLY.

Rules (must stay in sync with @src/notes/permissions.py ):
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
    FieldCondition,
    Filter,
    MatchValue,
    MinShould,
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
        Qdrant Filter ready to pass to client.query_points() query_filter parameter.

    Security:
        workspace_id is a `must` condition on every path.
        A developer CANNOT call this function without providing workspace_id.
    """
    workspace_condition = FieldCondition(
        key="workspace_id",
        match=MatchValue(value=workspace_id),
    )

    if role in ("owner", "admin"):
        return Filter(must=[workspace_condition])

    should_conditions = [
        FieldCondition(
            key="visibility",
            match=MatchValue(value="public"),
        ),
        FieldCondition(
            key="created_by",
            match=MatchValue(value=user_id),
        ),
    ]
    return Filter(
        must=[workspace_condition],
        should=should_conditions,
        min_should=MinShould(conditions=should_conditions, min_count=1),
    )
