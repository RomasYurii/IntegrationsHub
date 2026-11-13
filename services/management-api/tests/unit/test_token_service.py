import uuid
import pytest

from app.core.config import settings
from app.core.security import hash_refresh_token
from app.services.token_service import (
    consume_refresh_token,
    issue_refresh_token,
    revoke_refresh_token,
)


class FakeRedis:
    def __init__(self):
        self.store = {}  # key -> value
        self.ttl = {}    # key -> ex, щоб тест міг перевірити час життя

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex is not None:
            self.ttl[key] = ex

    async def getdel(self, key):
        self.ttl.pop(key, None)
        return self.store.pop(key, None)

    async def delete(self, key):
        self.ttl.pop(key, None)
        return 1 if self.store.pop(key, None) is not None else 0


@pytest.fixture
def fake_redis():
    return FakeRedis()


async def test_issue_refresh_token_stores_single_hashed_key(fake_redis):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)

    assert isinstance(token, str) and len(token) > 0
    refresh_keys = [k for k in fake_redis.store if k.startswith("refresh:")]
    assert len(refresh_keys) == 1
    assert all(token not in k for k in fake_redis.store)


async def test_issue_refresh_token_key_is_hashed_token(fake_redis):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)

    expected_key = f"refresh:{hash_refresh_token(token)}"
    assert expected_key in fake_redis.store


async def test_issue_refresh_token_value_and_ttl(fake_redis):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)

    # Перевіряємо єдиний створений ключ незалежно від його формату,
    # щоб тест 3 перевіряв саме значення та TTL навіть до фіксу ключа
    stored_key = next(iter(fake_redis.store))
    assert fake_redis.store[stored_key] == str(uid)
    assert fake_redis.ttl[stored_key] == settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def test_consume_refresh_token_returns_uuid(fake_redis):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)

    result = await consume_refresh_token(fake_redis, token)
    assert isinstance(result, uuid.UUID)
    assert result == uid


async def test_consume_refresh_token_is_one_time_use(fake_redis):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)

    first = await consume_refresh_token(fake_redis, token)
    second = await consume_refresh_token(fake_redis, token)

    assert first is not None
    assert second is None


async def test_consume_unknown_token_returns_none(fake_redis):
    result = await consume_refresh_token(fake_redis, "non-existent-refresh-token")
    assert result is None


async def test_revoke_refresh_token_removes_and_is_idempotent(fake_redis):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)
    assert len(fake_redis.store) == 1

    await revoke_refresh_token(fake_redis, token)
    assert len(fake_redis.store) == 0

    # Повторний revoke та revoke невідомого токена не кидають виняток
    await revoke_refresh_token(fake_redis, token)
    await revoke_refresh_token(fake_redis, "unknown-token")


async def test_consume_refresh_token_does_not_print_to_stdout(fake_redis, capsys):
    uid = uuid.uuid4()
    token = await issue_refresh_token(fake_redis, uid)

    await consume_refresh_token(fake_redis, token)
    captured = capsys.readouterr()
    assert captured.out == ""