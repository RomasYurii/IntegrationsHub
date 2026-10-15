import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.schemas.user import UserCreate
from app.core.security import *


class EmailAlreadyExistsError(Exception):
    pass

class IncorrectPasswordOrEmail(Exception):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def create_user(user: UserCreate, db: AsyncSession) -> User:
    email = _normalize_email(user.email)
    password_hash = await asyncio.to_thread(hash_password, user.password)

    new_user = User(email=email, password_hash=password_hash)
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise EmailAlreadyExistsError from None

    await db.refresh(new_user)
    return new_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await db.scalar(select(User).where(User.email == _normalize_email(email)))

    # Хешування рахуємо ЗАВЖДИ, навіть якщо користувача нема: інакше за часом
    # відповіді можна відрізнити "email не існує" від "пароль невірний".
    hash_to_check = user.password_hash if user else DUMMY_HASH
    password_ok = await asyncio.to_thread(verify_password, password, hash_to_check)

    if user is None or not password_ok or not user.is_active:
        return None

    # Тихо оновлюємо хеш, якщо параметри Argon2 з часом посилили
    if needs_rehash(user.password_hash):
        user.password_hash = await asyncio.to_thread(hash_password, password)
        await db.commit()

    return user
