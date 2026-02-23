import pytest

from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)


@pytest.mark.parametrize(
    "password",
    [
        "short-pass",
        "this-is-a-bit-longer-password-123",
        "x" * 200,  # very long password should still work
    ],
)
def test_hash_and_verify_password(password: str) -> None:
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password(password + "x", hashed)


def test_create_tokens() -> None:
    payload = {"sub": "123", "role": "owner"}

    access = create_access_token(payload)
    refresh = create_refresh_token(payload)

    assert isinstance(access, str) and access
    assert isinstance(refresh, str) and refresh

