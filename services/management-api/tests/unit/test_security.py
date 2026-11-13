import base64
import json
import uuid
from datetime import datetime, timezone, timedelta

import jwt
import pytest
import pytest_asyncio
from app.core.security import hash_password, verify_password, decode_access_token, create_access_token, \
    InvalidTokenError, hash_refresh_token, generate_refresh_token
from app.core.config import settings

def test_hash():

    assert "$argon2id$" in hash_password("dasdasdewqe312321")
    assert hash_password("asa") != hash_password("asa")

def test_verify_password():

    assert verify_password("aboba", hash_password("aboba")) is True
    assert verify_password("aboba", hash_password("abb")) is False

def test_verify_broken():

    passw = hash_password("aboba")
    passw = passw.replace("$argon2id$", "31231")

    assert verify_password("aboba", passw) is False

def test_access_token_roundtrip():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = decode_access_token(token)

    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"


def test_forged_token_raises_invalid_token_error():
    uid = uuid.uuid4()
    token = create_access_token(uid)

    # Підробляємо підпис токена (змінюємо останній символ)
    last_char = "a" if token[-1] != "a" else "b"
    forged_token = token[:-1] + last_char

    with pytest.raises(InvalidTokenError):
        decode_access_token(forged_token)


def test_expired_token_raises_invalid_token_error():
    uid = uuid.uuid4()
    expired_payload = {
        "sub": str(uid),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    # Використовуємо алгоритм із налаштувань (за замовчуванням HS256)
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    expired_token = jwt.encode(
        expired_payload,
        settings.SECRET_KEY,
        algorithm=algorithm,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired_token)


def test_refresh_token_rejected_as_access_token():
    uid = uuid.uuid4()
    refresh_payload = {
        "sub": str(uid),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    token_with_refresh_type = jwt.encode(
        refresh_payload,
        settings.SECRET_KEY,
        algorithm=algorithm,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token_with_refresh_type)


def test_alg_none_token_rejected():
    uid = uuid.uuid4()
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "sub": str(uid),
        "type": "access",
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
    }

    def b64url(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    # Формуємо непідписаний JWT формату header.payload.
    unsigned_token = f"{b64url(header)}.{b64url(payload)}."

    with pytest.raises(InvalidTokenError):
        decode_access_token(unsigned_token)


def test_hash_refresh_token_properties():
    raw_token = "sample-refresh-token-value"
    hash_1 = hash_refresh_token(raw_token)
    hash_2 = hash_refresh_token(raw_token)

    # Детермінованість
    assert hash_1 == hash_2
    # Довжина 64 hex-символи (SHA-256)
    assert len(hash_1) == 64
    assert all(c in "0123456789abcdef" for c in hash_1)
    # Не збігається з оригінальним токеном
    assert hash_1 != raw_token


def test_generate_refresh_token_uniqueness_and_length():
    token_1 = generate_refresh_token()
    token_2 = generate_refresh_token()

    assert token_1 != token_2
    assert len(token_1) == 64
    assert len(token_2) == 64