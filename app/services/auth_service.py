from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.models.user import User
from app.models.token import TokenData
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Security, Depends
from app.services.user_service import get_user_by_email
from fastapi.security import OAuth2PasswordBearer
from app.db.database import get_db
from passlib.context import CryptContext
import uuid
import logging

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class ErrorMessages:
    """Klasa zawierająca komunikaty błędów."""
    USER_NOT_FOUND = "Użytkownik nie został znaleziony"
    INVALID_CREDENTIALS = "Nieprawidłowe dane logowania"
    SERVER_ERROR = "Wystąpił błąd serwera"

class AccountBlockedError(Exception):
    """Wyjątek rzucany gdy konto jest zablokowane."""
    pass

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

class AuthService:
    """Serwis do obsługi autoryzacji i uwierzytelniania."""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Weryfikuje hasło."""
        return User.verify_password(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generuje hash hasła."""
        return User.get_password_hash(password)

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Uwierzytelnia użytkownika."""
        try:
            user = await get_user_by_email(db, email)
            if not user:
                self._last_error = ErrorMessages.USER_NOT_FOUND
                return None
            if not self.verify_password(password, user.hashed_password):
                self._last_error = ErrorMessages.INVALID_CREDENTIALS
                await self._log_failed_login(db, email)
                return None
            await self._log_successful_login(db, user)
            return user
        except Exception as e:
            logger.error(f"Błąd podczas uwierzytelniania: {str(e)}")
            self._last_error = ErrorMessages.SERVER_ERROR
            return None

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Tworzy token dostępu z dodatkowymi zabezpieczeniami."""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))
        
        # Dodaj dodatkowe claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # Unikalny identyfikator tokenu
            "type": "access"  # Typ tokenu
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    async def get_current_user(self, token: str, db: AsyncSession) -> User:
        """Pobiera aktualnego użytkownika na podstawie tokenu."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
            token_data = TokenData(email=email)
        except JWTError:
            raise credentials_exception
        user = await get_user_by_email(db, token_data.email)
        if user is None:
            raise credentials_exception
        return user

    async def get_current_active_user(self, user: User = Security(get_current_user)) -> User:
        """Pobiera aktualnego aktywnego użytkownika."""
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return user

    async def get_current_admin(self, user: User = Security(get_current_active_user)) -> User:
        """Pobiera aktualnego użytkownika z uprawnieniami administratora."""
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return user

    async def _check_login_attempts(self, db: AsyncSession, email: str) -> None:
        """Sprawdza liczbę nieudanych prób logowania."""
        attempts = await self._get_failed_login_attempts(db, email)
        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            await self._block_account(db, email)
            raise AccountBlockedError(
                f"Konto zostało zablokowane po {attempts} nieudanych próbach logowania"
            )

# Tworzymy globalną instancję serwisu
auth_service = AuthService()

# Eksportujemy funkcje
async def get_current_user(token: str = Security(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """Pobiera aktualnego użytkownika na podstawie tokenu."""
    return await auth_service.get_current_user(token, db)

async def get_current_active_user(user: User = Security(get_current_user)) -> User:
    """Pobiera aktualnego aktywnego użytkownika."""
    return await auth_service.get_current_active_user(user)

async def get_current_admin(user: User = Security(get_current_active_user)) -> User:
    """Pobiera aktualnego użytkownika z uprawnieniami administratora."""
    return await auth_service.get_current_admin(user)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tworzy token dostępu."""
    return auth_service.create_access_token(data, expires_delta)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikuje hasło."""
    return auth_service.verify_password(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generuje hash hasła."""
    return auth_service.get_password_hash(password) 