from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional

class TokenData(BaseModel):
    """Schema danych tokenu JWT."""
    email: str
    scopes: List[str] = []
    exp: Optional[datetime] = None
    jti: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RevokedToken(Base):
    """Model unieważnionego tokenu w bazie danych."""
    __tablename__ = "revoked_tokens"
    __table_args__ = (
        Index('idx_revoked_tokens_jti_expires', 'jti', 'expires_at'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

class PasswordResetToken(Base):
    """Model tokenu resetowania hasła w bazie danych."""
    __tablename__ = "password_reset_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    
    # Relacja z użytkownikiem
    user = relationship("User", backref="reset_tokens")

class PasswordResetAttempt(Base):
    """Model próby resetowania hasła w bazie danych."""
    __tablename__ = "password_reset_attempts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    attempt_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=False)

class TokenCreate(BaseModel):
    """Schema do tworzenia nowego tokenu."""
    access_token: str = Field(..., description="Token dostępu JWT")
    token_type: str = Field("bearer", description="Typ tokenu")
    expires_in: int = Field(..., description="Czas wygaśnięcia tokenu w sekundach")

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    """Schema do zwracania informacji o tokenie."""
    access_token: str
    token_type: str
    expires_in: int

    model_config = ConfigDict(from_attributes=True) 