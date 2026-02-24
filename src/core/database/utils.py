from typing import Any

from sqlalchemy.sql import ColumnElement


def tenant_filter(model: Any, workspace_id: int) -> ColumnElement[bool]:
    """
    Build a workspace filter expression for a given SQLAlchemy model.

    By convention, new multi-tenant models should use `workspace_id`. For
    legacy models that still use `tenant_id`, we fall back to that attribute.
    """

    if hasattr(model, "workspace_id"):
        return model.workspace_id == workspace_id
    if hasattr(model, "tenant_id"):
        return model.tenant_id == workspace_id

    raise AttributeError(
        f"{model!r} has neither 'workspace_id' nor 'tenant_id'; "
        "it cannot be used with tenant_filter()."
    )
