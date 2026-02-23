from datetime import datetime, timedelta
from hashlib import sha256

from jose import jwt
from passlib.context import CryptContext

from config import settings


# Use PBKDF2-SHA256 to avoid bcrypt backend / 72-byte issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _normalize_password(password: str) -> str:
    """Normalize password input so bcrypt backend length limits are not a problem."""
    # Use SHA-256 to turn any-length input into fixed 64-hex-char string
    return sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(_normalize_password(password), hashed)


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