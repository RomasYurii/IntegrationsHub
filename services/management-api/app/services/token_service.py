import uuid
from redis.asyncio import Redis

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_refresh_token


REFRESH_PREFIX = "refresh:"

def _refresh_key(raw_token: str) -> str:
    return f"{REFRESH_PREFIX}{hash_refresh_token(raw_token)}"


async def issue_refresh_token(redis: Redis, user_id) -> str:
    """ генерує токен, записує refresh:{хеш} зі значенням user_id і TTL, повертає сам токен"""

    raw_token = generate_refresh_token()
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.set(_refresh_key(raw_token), str(user_id), ex=ttl_seconds)
    return raw_token


async def consume_refresh_token(redis: Redis, raw_token: str) -> uuid.UUID | None:
    user_id_str = await redis.getdel(_refresh_key(raw_token))
    if user_id_str is None:
        return None
    if isinstance(user_id_str, bytes):
        user_id_str = user_id_str.decode("utf-8")
    return uuid.UUID(user_id_str)


async def revoke_refresh_token(redis: Redis, raw_token: str) -> None:
    await redis.delete(_refresh_key(raw_token))
