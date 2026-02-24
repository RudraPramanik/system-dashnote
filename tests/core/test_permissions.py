import asyncio

import pytest
from fastapi import HTTPException

from core.security.context import RequestContext
from core.security.permissions import require_roles


def test_require_roles_allows_owner_and_admin() -> None:
    checker = require_roles("owner", "admin")

    ctx_owner = RequestContext(user_id=1, workspace_id=1, role="owner")
    ctx_admin = RequestContext(user_id=2, workspace_id=1, role="admin")

    # direct call, bypassing FastAPI dependency injection
    owner_result = asyncio.run(checker(ctx=ctx_owner))
    admin_result = asyncio.run(checker(ctx=ctx_admin))

    assert owner_result is ctx_owner
    assert admin_result is ctx_admin


def test_require_roles_forbids_member() -> None:
    checker = require_roles("owner", "admin")
    ctx_member = RequestContext(user_id=3, workspace_id=1, role="member")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(checker(ctx=ctx_member))

    assert exc.value.status_code == 403
    assert "Insufficient permissions" in exc.value.detail

