from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.models import User
from app.schemas.token import Token
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
):
    # Стандарт OAuth2 називає поле "username", але ми кладемо туди email
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user