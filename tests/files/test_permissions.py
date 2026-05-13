from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from files.permissions import (
    assert_can_modify,
    assert_can_read,
    can_modify,
    can_read,
)


def test_owner_can_read_any(owner_ctx, own_private, other_private, public_file):
    assert can_read(own_private, owner_ctx) is True
    assert can_read(other_private, owner_ctx) is True
    assert can_read(public_file, owner_ctx) is True


def test_admin_can_read_any(admin_ctx, own_private, other_private, public_file):
    assert can_read(own_private, admin_ctx) is True
    assert can_read(other_private, admin_ctx) is True
    assert can_read(public_file, admin_ctx) is True


def test_member_reads_own_private(member_ctx, own_private):
    assert can_read(own_private, member_ctx) is True


def test_member_cannot_read_others_private(member_ctx, other_private):
    assert can_read(other_private, member_ctx) is False


def test_member_reads_public(member_ctx, public_file):
    assert can_read(public_file, member_ctx) is True


def test_owner_can_modify_any(owner_ctx, own_private, other_private):
    assert can_modify(own_private, owner_ctx) is True
    assert can_modify(other_private, owner_ctx) is True


def test_member_can_modify_own(member_ctx, own_private):
    assert can_modify(own_private, member_ctx) is True


def test_member_cannot_modify_others(member_ctx, other_private):
    assert can_modify(other_private, member_ctx) is False


def test_assert_can_read_raises_403(member_ctx, other_private):
    with pytest.raises(HTTPException) as exc_info:
        assert_can_read(other_private, member_ctx)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "No permission to access this file."


def test_assert_can_modify_raises_403(member_ctx, other_private):
    with pytest.raises(HTTPException) as exc_info:
        assert_can_modify(other_private, member_ctx)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "No permission to modify this file."
