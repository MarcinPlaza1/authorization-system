import logging
from fastapi import APIRouter, Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.auth_service import (
    get_current_user, create_access_token, 
    get_current_active_user, get_current_admin,
    verify_password, get_password_hash
)
from app.services.user_service import create_user, get_user_by_id, authenticate_user, get_user_by_email, get_user_by_username
from app.services.role_service import assign_role_to_user
from app.services.token_service import token_service
from app.services.password_service import (
    create_password_reset_token,
    verify_reset_token,
    reset_password
)
from app.services.email_service import email_service
from app.services.audit_service import log_security_event, get_failed_login_attempts
from app.core.config import settings
from jose import jwt
from typing import List, Annotated
from pydantic import BaseModel, EmailStr, constr
from datetime import datetime, timedelta
import re
import os
import httpx
from app.models.errors import ErrorDetail, ErrorTypes, ErrorMessages, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()

class UserBase(BaseModel):
    email: EmailStr
    username: str = constr(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")

class UserCreate(UserBase):
    password: str = constr(min_length=8)
    full_name: str = constr(min_length=2, max_length=100)

    def validate_password(self):
        """Sprawdza, czy hasło spełnia wymogi bezpieczeństwa."""
        if not re.search(r"[A-Z]", self.password):
            raise ValueError("Hasło musi zawierać przynajmniej jedną wielką literę")
        if not re.search(r"[a-z]", self.password):
            raise ValueError("Hasło musi zawierać przynajmniej jedną małą literę")
        if not re.search(r"\d", self.password):
            raise ValueError("Hasło musi zawierać przynajmniej jedną cyfrę")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", self.password):
            raise ValueError("Hasło musi zawierać przynajmniej jeden znak specjalny")

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    email: str
    scopes: List[str] = []

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = constr(min_length=8)

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = constr(min_length=8)

class CaptchaVerification(BaseModel):
    captcha_token: str

class UserResponse(UserBase):
    id: int
    full_name: str
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

async def verify_captcha(captcha_token: str) -> bool:
    """Weryfikuje token reCAPTCHA."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": os.getenv("RECAPTCHA_SECRET_KEY"),
                "response": captcha_token
            }
        )
        result = response.json()
        return result.get("success", False)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Walidacja hasła
        try:
            user.validate_password()
        except ValueError as e:
            raise ValueError("Błąd walidacji hasła", str(e))
        
        # Sprawdzenie czy email jest już zajęty
        existing_user = await get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Błąd walidacji", "detail": "Email jest już zarejestrowany"}
            )
        
        # Sprawdzenie czy nazwa użytkownika jest już zajęta
        existing_user = await get_user_by_username(db, user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Błąd walidacji", "detail": "Nazwa użytkownika jest już zajęta"}
            )
        
        # Utworzenie użytkownika
        new_user = await create_user(
            db, 
            user.email, 
            user.username, 
            user.password,
            user.full_name
        )
        await assign_role_to_user(db, new_user.id, "user")
        return new_user
        
    except Exception as e:
        logger.error(f"Błąd podczas rejestracji użytkownika: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code=500,
                    message=ErrorMessages.SERVER_ERROR,
                    type=ErrorTypes.SERVER_ERROR,
                    details=str(e)
                )
            ).dict()
        )

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    captcha: CaptchaVerification = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    # Sprawdź czy nie przekroczono limitu prób
    failed_attempts = await get_failed_login_attempts(db, form_data.username)
    if failed_attempts >= 3:
        # Wymagaj CAPTCHA po 3 nieudanych próbach
        if not captcha or not await verify_captcha(captcha.captcha_token):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Za dużo prób logowania. Wymagana weryfikacja CAPTCHA"
            )
    
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Loguj nieudaną próbę
        await log_security_event(
            db, "failed_login",
            request,
            email=form_data.username,
            details={"reason": "invalid_credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Loguj udane logowanie
    await log_security_event(
        db, "successful_login",
        request,
        user_id=user.id,
        email=user.email
    )
    
    scopes = [role.name for role in user.roles]
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "scopes": scopes,
            "user_id": user.id
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800
    }

@router.get("/me", response_model=User)
async def read_users_me(
    current_user = Security(get_current_active_user)
):
    return current_user

@router.get("/users/{user_id}", response_model=User)
async def read_user(
    user_id: int,
    current_user = Security(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Tylko admin może przeglądać innych użytkowników
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień do przeglądania innych użytkowników"
        )
    
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie został znaleziony"
        )
    return user 

@router.post("/logout")
async def logout(
    current_user = Security(get_current_active_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="api/users/token")),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Dekoduj token aby uzyskać jti i exp
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(
            jti=payload.get("jti"),
            exp=payload.get("exp")
        )
        
        # Unieważnij token
        success, error = await token_service.revoke_token(db, token_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Błąd podczas wylogowywania: {error}"
            )
        
        return {"message": "Pomyślnie wylogowano"}
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user = Security(get_current_active_user),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        await log_security_event(
            db, "failed_password_change",
            request,
            user_id=current_user.id,
            details={"reason": "invalid_current_password"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowe aktualne hasło"
        )
    
    try:
        UserCreate(
            email=current_user.email,
            username=current_user.username,
            password=password_data.new_password
        ).validate_password()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    # Loguj zmianę hasła
    await log_security_event(
        db, "password_changed",
        request,
        user_id=current_user.id
    )
    
    # Wyślij powiadomienie email
    await email_service.send_password_change_notification(current_user.email)
    
    return {"message": "Hasło zostało zmienione"}

@router.post("/reset-password")
async def request_password_reset(
    reset_data: PasswordReset,
    captcha: CaptchaVerification,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Wymagaj CAPTCHA dla wszystkich prób resetowania hasła
    if not await verify_captcha(captcha.captcha_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa weryfikacja CAPTCHA"
        )
    
    user = await get_user_by_email(db, reset_data.email)
    if not user:
        # Loguj próbę dla nieistniejącego użytkownika
        await log_security_event(
            db, "failed_password_reset_request",
            request,
            email=reset_data.email,
            details={"reason": "user_not_found"}
        )
        return {"message": "Jeśli konto istnieje, instrukcje resetowania hasła zostały wysłane na podany adres email"}
    
    # Generuj token resetowania
    token = await create_password_reset_token(db, user, request.client.host)
    
    # Wyślij email z linkiem
    await email_service.send_password_reset_email(user.email, token)
    
    # Loguj żądanie resetowania
    await log_security_event(
        db, "password_reset_requested",
        request,
        user_id=user.id
    )
    
    return {"message": "Instrukcje resetowania hasła zostały wysłane na podany adres email"}

@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Potwierdzenie resetowania hasła."""
    try:
        # Walidacja nowego hasła
        UserCreate(
            email="temp@example.com",
            username="temp",
            password=reset_data.new_password
        ).validate_password()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Resetuj hasło
    user = await reset_password(db, reset_data.token, reset_data.new_password)
    return {"message": "Hasło zostało zresetowane"} 