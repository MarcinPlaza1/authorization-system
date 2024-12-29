from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from fastapi import HTTPException, status
import re
from sqlalchemy.orm import selectinload

async def get_user_by_email(db: AsyncSession, email: str):
    stmt = (
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))  # Eager loading
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

def validate_email(email: str) -> bool:
    """Sprawdza poprawność adresu email."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

async def create_user(db: AsyncSession, email: str, username: str, password: str, full_name: str = None):
    # Walidacja email
    if not validate_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy format adresu email"
        )

    # Sprawdzenie czy email jest już zajęty
    if await get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email jest już zarejestrowany"
        )

    # Sprawdzenie czy nazwa użytkownika jest już zajęta
    if await get_user_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nazwa użytkownika jest już zajęta"
        )
    
    return await User.create(db, email, username, password, full_name)

async def authenticate_user(db: AsyncSession, email: str, password: str):
    """Uwierzytelnia użytkownika."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not user.verify_password(password):
        return None
    return user 