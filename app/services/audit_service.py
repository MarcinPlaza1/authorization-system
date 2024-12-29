from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import Session

from app.db.database import Base


class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    username = Column(String, nullable=False)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=func.now())
    details = Column(String)


async def log_security_event(db: Session, event_type: str, username: str, ip_address: str = None, details: str = None):
    log_entry = SecurityAuditLog(
        event_type=event_type,
        username=username,
        ip_address=ip_address,
        details=details
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry


async def get_failed_login_attempts(db: Session, username: str, minutes: int = 30) -> int:
    cutoff_time = func.now() - func.interval(f'{minutes} minutes')
    return db.query(SecurityAuditLog).filter(
        SecurityAuditLog.username == username,
        SecurityAuditLog.event_type == 'failed_login',
        SecurityAuditLog.timestamp >= cutoff_time
    ).count() 