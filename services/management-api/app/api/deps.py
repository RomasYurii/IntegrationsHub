import logging
import uuid

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_db
from app.core.permissions import Role
from app.core.security import InvalidTokenError, decode_access_token
from app.models import User, Membership
from app.services.tenant_service import TenantDoesntExist

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


async def get_membership(
        tenant_id: uuid.UUID,  # FastAPI автоматично візьме з path-параметра /{tenant_id}
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
) -> Membership:
    stmt = select(Membership).where(
        Membership.tenant_id == tenant_id,
        Membership.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    if membership is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    return membership


def require_role(min_role):
    async def checker(
            membership: Membership = Depends(get_membership)
    ) -> Membership:

        role = Role[membership.role] if isinstance(membership.role, str) else membership.role

        if role < min_role:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return membership

    return checker
