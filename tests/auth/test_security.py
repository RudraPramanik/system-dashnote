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
    ],
)
def test_hash_and_verify_password(password: str) -> None:
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password(password + "x", hashed)


def test_bcrypt_rejects_password_over_72_bytes() -> None:
    # bcrypt has a 72-byte input limit; we reject longer passwords explicitly
    too_long = "x" * 200
    with pytest.raises(ValueError):
        hash_password(too_long)


def test_create_tokens() -> None:
    payload = {"sub": "123", "role": "owner"}

    access = create_access_token(payload)
    refresh = create_refresh_token(payload)

    assert isinstance(access, str) and access
    assert isinstance(refresh, str) and refresh

