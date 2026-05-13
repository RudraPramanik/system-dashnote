from unittest.mock import MagicMock

import pytest

from core.security.context import RequestContext


@pytest.fixture
def owner_ctx() -> RequestContext:
    return RequestContext(user_id=1, workspace_id=10, role="owner")


@pytest.fixture
def admin_ctx() -> RequestContext:
    return RequestContext(user_id=2, workspace_id=10, role="admin")


@pytest.fixture
def member_ctx() -> RequestContext:
    return RequestContext(user_id=42, workspace_id=10, role="member")


@pytest.fixture
def own_private(member_ctx: RequestContext) -> MagicMock:
    f = MagicMock()
    f.is_private = True
    f.created_by = member_ctx.user_id
    return f


@pytest.fixture
def other_private(member_ctx: RequestContext) -> MagicMock:
    f = MagicMock()
    f.is_private = True
    f.created_by = member_ctx.user_id + 999
    return f


@pytest.fixture
def public_file() -> MagicMock:
    f = MagicMock()
    f.is_private = False
    f.created_by = 999
    return f
