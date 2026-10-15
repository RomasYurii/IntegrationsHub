import logging
import uuid

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_access_token
from app.models import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError, KeyError) as e:
        # Причину пишемо в лог, а клієнту віддаємо загальну відповідь
        logger.info("Token rejected: %s", e)
        raise credentials_exception from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user