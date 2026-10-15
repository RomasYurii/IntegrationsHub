import uuid
import redis as rredis

from app.core.config import settings
from app.core.security import generate_refresh_token


"""
issue_refresh_token(redis, user_id) -> str: генерує токен, записує refresh:{хеш} зі значенням user_id і TTL, повертає сам токен;
"""
class RedisIssue(Exception):
    pass


async def issue_refresh_token(redis, user_id) -> str:
    """ генерує токен, записує refresh:{хеш} зі значенням user_id і TTL, повертає сам токен"""
    try:
        token = generate_refresh_token()
        await redis.set(f"refresh:{token}", f"{user_id}", ex=settings.REFRESH_TOKEN_EXPIRE_DAYS*24*3600)
        return token

    except rredis.ResponseError:
        raise RedisIssue from None


    return token

"""
consume_refresh_token(redis, token) -> uuid.UUID | None: атомарно дістає й видаляє запис, повертає user_id або None;
revoke_refresh_token(redis, token) -> None: просто видаляє запис.
"""

async def consume_refresh_token(redis, token) -> uuid.UUID| None:
    """атомарно дістає й видаляє запис, повертає user_id або None"""
    try:
        print(token)
        r = await redis.getdel(f"refresh:{token}")

    except rredis.ResponseError:
        raise RedisIssue from None

    return r

async def revoke_refresh_token(redis, token) -> None:
    """просто видаляє запис"""
    try:
        await redis.delete(f"refresh:{token}")
    except rredis.ResponseError:
        raise RedisIssue from None
