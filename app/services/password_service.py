from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.token import PasswordResetToken
from app.models.user import User
from fastapi import HTTPException, status
from app.services.auth_service import get_password_hash
import secrets
import string

# Konfiguracja
RESET_TOKEN_LENGTH = 32
RESET_TOKEN_EXPIRE_MINUTES = 30

def generate_reset_token() -> str:
    """Generuje bezpieczny token resetowania hasła."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(RESET_TOKEN_LENGTH))

async def create_password_reset_token(
    db: AsyncSession,
    user: User,
    ip_address: str
) -> str:
    """Tworzy token resetowania hasła."""
    # Unieważnij wszystkie poprzednie tokeny użytkownika
    await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id)
        .update({"used": True})
    )
    await db.commit()
    
    # Generuj nowy token
    token = generate_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        ip_address=ip_address,
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    )
    
    db.add(reset_token)
    await db.commit()
    return token

async def verify_reset_token(
    db: AsyncSession,
    token: str
) -> User:
    """Weryfikuje token resetowania hasła i zwraca użytkownika."""
    result = await db.execute(
        select(PasswordResetToken)
        .where(
            and_(
                PasswordResetToken.token == token,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > datetime.utcnow()
            )
        )
    )
    reset_token = result.scalar_one_or_none()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy lub wygasły token resetowania hasła"
        )
    
    return reset_token.user

async def reset_password(
    db: AsyncSession,
    token: str,
    new_password: str
) -> User:
    """Resetuje hasło użytkownika."""
    # Weryfikuj token i pobierz użytkownika
    user = await verify_reset_token(db, token)
    
    # Oznacz token jako użyty
    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token == token)
    )
    reset_token = result.scalar_one()
    reset_token.used = True
    
    # Zaktualizuj hasło
    user.hashed_password = get_password_hash(new_password)
    
    await db.commit()
    return user 