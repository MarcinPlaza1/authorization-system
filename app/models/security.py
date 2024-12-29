from sqlalchemy import Column, Integer, String, DateTime, MetaData
from sqlalchemy.sql import func
from app.db.database import Base
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class SecurityAuditLog(Base):
    """Model do przechowywania logów audytowych bezpieczeństwa."""
    __tablename__ = "security_audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    event_type = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=False)  # Maksymalna długość dla IPv6
    user_agent = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=True)
    details = Column(String(1000), nullable=True)

class SecurityAuditLogCreate(BaseModel):
    """Schema do walidacji danych wejściowych dla logów audytowych."""
    event_type: str = Field(..., max_length=50)
    ip_address: str = Field(..., max_length=45)
    user_agent: str = Field(..., max_length=255)
    user_id: Optional[int] = None
    details: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True) 