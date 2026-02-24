from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from config import settings


# Prefer bcrypt for new hashes, but allow verifying older pbkdf2_sha256 hashes if any exist
pwd_context = CryptContext(
    schemes=["bcrypt", "pbkdf2_sha256"],
    deprecated=["pbkdf2_sha256"],
)


def _password_too_long(password: str) -> bool:
    # bcrypt operates on bytes; limit is 72 bytes
    return len(password.encode("utf-8")) > 72


def hash_password(password: str) -> str:
    # user requested "bcrypt" without sha256 prehashing; enforce bcrypt length limit explicitly
    if _password_too_long(password):
        raise ValueError("Password must be <= 72 bytes for bcrypt")
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if _password_too_long(password):
        return False
    try:
        return pwd_context.verify(password, hashed)
    except UnknownHashError:
        # hash in DB isn't recognized by passlib (corrupt or legacy) -> treat as invalid credentials
        return False


def create_access_token(data: dict, expires_minutes: int = 15) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(data: dict, expires_days: int = 30) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=expires_days)
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")
# from datetime import datetime, timedelta
# from jose import jwt
# from passlib.context import CryptContext
# from config import settings

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)

# def verify_password(password: str, hashed: str) -> bool:
#     return pwd_context.verify(password, hashed)

# def create_access_token(data: dict, expires_minutes: int = 15):
#     payload = data.copy()
#     payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
#     return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

# def create_refresh_token(data: dict, expires_days: int = 30):
#     payload = data.copy()
#     payload["exp"] = datetime.utcnow() + timedelta(days=expires_days)
#     return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")