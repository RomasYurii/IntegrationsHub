import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher, exceptions

from app.core.config import settings

ph = PasswordHasher()


class InvalidTokenError(Exception):
    """Наш власний виняток: решта коду нічого не знає про PyJWT."""


# ---------- Паролі ----------

def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)
    except (exceptions.VerificationError, exceptions.InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """True, якщо хеш зроблений за застарілими параметрами Argon2."""
    return ph.check_needs_rehash(hashed_password)


# Фіктивний хеш для захисту від timing-атаки при логіні неіснуючого користувача.
# Обчислюється один раз при імпорті модуля.
DUMMY_HASH = ph.hash("dummy-password-for-timing")


# ---------- JWT ----------

def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],  # явний список: захист від "alg: none"
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as e:  # покриває і прострочений, і підроблений, і зіпсований
        raise InvalidTokenError(str(e)) from e

    if payload.get("type") != "access":
        raise InvalidTokenError("Wrong token type")
    return payload