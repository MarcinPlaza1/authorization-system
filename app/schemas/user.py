from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class RoleCreate(BaseModel):
    """Schema do tworzenia nowej roli."""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)

class RoleResponse(BaseModel):
    """Schema do zwracania danych roli."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    """Schema do tworzenia nowego użytkownika."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    """Schema do aktualizacji danych użytkownika."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    """Schema do zwracania danych użytkownika."""
    id: int
    email: str
    username: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    roles: List[RoleResponse] = []

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    """Schema do logowania użytkownika."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    """Schema do zwracania tokenów."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

    model_config = ConfigDict(from_attributes=True) 