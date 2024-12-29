from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Table, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

# Tabela asocjacyjna dla relacji many-to-many między rolami a uprawnieniami
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)

class Permission(Base):
    """Model uprawnień w systemie."""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class Role(Base):
    """Model ról w systemie."""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", back_populates="role")

class User(Base):
    """Model użytkownika w systemie."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role_id = Column(Integer, ForeignKey('roles.id'))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    role = relationship("Role", back_populates="users")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    access_tokens = relationship("AccessToken", back_populates="user")
    security_logs = relationship("SecurityAuditLog", back_populates="user")

class PasswordResetToken(Base):
    """Model tokenu resetowania hasła."""
    
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="password_reset_tokens")

class AccessToken(Base):
    """Model tokenu dostępu."""
    
    __tablename__ = "access_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="access_tokens")

class SecurityAuditLog(Base):
    """Model logów bezpieczeństwa."""
    
    __tablename__ = "security_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    event_type = Column(String(50))
    event_date = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    details = Column(Text)
    
    user = relationship("User", back_populates="security_logs") 