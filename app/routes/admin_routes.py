from fastapi import APIRouter, Depends, HTTPException, status, Security, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.db.database import get_db
from app.services.auth_service import get_current_admin
from app.services.user_service import get_user_by_id
from app.services.role_service import assign_role_to_user, remove_role_from_user
from app.services.audit_service import log_security_event, SecurityAuditLog
from app.models.user import User, Role
from app.models.errors import ErrorDetail, ErrorTypes, ErrorMessages, ErrorResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter()

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    roles: List[str]

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_admin = Security(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Lista użytkowników z możliwością filtrowania i wyszukiwania."""
    query = select(User)
    
    # Zastosuj filtry
    if search:
        query = query.where(
            or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%")
            )
        )
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role:
        query = query.join(User.roles).where(Role.name == role)
    
    # Paginacja
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        UserResponse(
            **user.__dict__,
            roles=[role.name for role in user.roles]
        ) for user in users
    ]

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: int,
    current_admin = Security(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Szczegółowe informacje o użytkowniku."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie został znaleziony"
        )
    
    return UserResponse(
        **user.__dict__,
        roles=[role.name for role in user.roles]
    )

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_admin = Security(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code=404,
                    message=ErrorMessages.RESOURCE_NOT_FOUND,
                    type=ErrorTypes.NOT_FOUND
                )
            ).dict()
        )
    
    # Aktualizacja użytkownika
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(user, field, value)
    
    await db.commit()
    return UserResponse.model_validate(user)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin = Security(get_current_admin),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Usunięcie użytkownika."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie został znaleziony"
        )
    
    # Nie pozwól na usunięcie własnego konta
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie można usunąć własnego konta administratora"
        )
    
    # Loguj usunięcie użytkownika
    await log_security_event(
        db,
        "user_deleted",
        request,
        user_id=user.id,
        details={"email": user.email}
    )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "Użytkownik został usunięty"}

@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    event_type: Optional[str] = None,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_admin = Security(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Przeglądanie logów bezpieczeństwa."""
    query = select(SecurityAuditLog)
    
    # Zastosuj filtry
    if event_type:
        query = query.where(SecurityAuditLog.event_type == event_type)
    if user_id:
        query = query.where(SecurityAuditLog.user_id == user_id)
    if email:
        query = query.where(SecurityAuditLog.email.ilike(f"%{email}%"))
    if start_date:
        query = query.where(SecurityAuditLog.created_at >= start_date)
    if end_date:
        query = query.where(SecurityAuditLog.created_at <= end_date)
    
    # Sortuj po dacie (najnowsze pierwsze)
    query = query.order_by(SecurityAuditLog.created_at.desc())
    
    # Paginacja
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs 