from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from redis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import await_

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.services.token_service import consume_refresh_token, issue_refresh_token, revoke_refresh_token
from app.models import User
from app.schemas.token import Token, RefreshRequest
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import (
    EmailAlreadyExistsError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(
        user: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    try:
        return await create_user(user, db)

    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered")



@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis : Redis = Depends(get_redis),
):
    # Стандарт OAuth2 називає поле "username", але ми кладемо туди email
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id), refresh_token= await issue_refresh_token(redis, user.id))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


"""
POST /auth/refresh: приймає RefreshRequest. Алгоритм: спожити токен, якщо None, то 401;
 знайти користувача й перевірити is_active (інакше 401); видати нову пару (новий refresh теж проходить через issue_refresh_token).
"""
@router.post("/refresh", response_model=Token)
async def refresh(
        token: RefreshRequest,
        redis : Redis = Depends(get_redis),
        db: AsyncSession = Depends(get_db)

):
    uid = await consume_refresh_token(redis, token.refresh_token)
    if uid is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.scalar(select(User).where(User.id == uid))
    if (user is None) or (not user.is_active):
        raise HTTPException(status_code=401, detail="Invalid token")


    return Token(access_token=create_access_token(user.id), refresh_token=await issue_refresh_token(redis,user.id))

"""
POST /auth/logout: приймає RefreshRequest, відкликає токен, завжди повертає 204 без тіла.
"""

@router.post("/logout", status_code=204)
async def logout(
        token: RefreshRequest,
        redis : Redis = Depends(get_redis)
):
    await revoke_refresh_token(redis, token.refresh_token)
