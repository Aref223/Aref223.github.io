from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from ..config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fernet: Optional[Fernet] = Fernet(settings.FERNET_KEY) if settings.FERNET_KEY else None


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(tz=timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": subject}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def encrypt_value(value: str) -> str:
    if not fernet:
        return value
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    if not fernet:
        return value
    return fernet.decrypt(value.encode()).decode()