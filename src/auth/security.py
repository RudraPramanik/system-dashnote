from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")
def hast_password(password: str) -> str:
    return pwd_context.hash(password)
def verify_password(password:str, hashed:str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(data:dict, expires_minutes: int=15):
    payLoad = data.copy()
    payLoad["exp"] = datetime.utctimetuple() + timedelta(minutes=expires_minutes)
    return jwt.encode(payLoad, settings.JWT_SECRET,algorithm="HS256")
def create_refresh_token(data: dict, expires_days:int=30):
    payLoad = data.copy()
    payLoad["exp"] = datetime.utctimetuple() + timedelta(days=expires_days)
    return jwt.encode(payLoad, settings.JWT_REFRESH_SECRET, algorithm="HS256")
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