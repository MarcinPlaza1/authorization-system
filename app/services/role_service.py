from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.user import Role, User, Permission
from fastapi import HTTPException, status
from typing import List, Set
from functools import lru_cache

async def get_role_by_name(db: AsyncSession, name: str):
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.name == name)
    )
    return result.scalar_one_or_none()

async def create_role(db: AsyncSession, name: str, description: str = None, parent_role_names: List[str] = None):
    if await get_role_by_name(db, name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role {name} already exists"
        )
    
    role = Role(name=name, description=description)
    db.add(role)
    
    if parent_role_names:
        for parent_name in parent_role_names:
            parent_role = await get_role_by_name(db, parent_name)
            if parent_role:
                role.parent_roles.append(parent_role)
    
    await db.commit()
    await db.refresh(role)
    return role

async def get_or_create_permission(
    db: AsyncSession,
    name: str,
    resource: str,
    action: str,
    description: str = None
) -> Permission:
    result = await db.execute(
        select(Permission).where(Permission.name == name)
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description
        )
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
    
    return permission

async def assign_permission_to_role(
    db: AsyncSession,
    role_name: str,
    permission_name: str
) -> Role:
    role = await get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    result = await db.execute(
        select(Permission).where(Permission.name == permission_name)
    )
    permission = result.scalar_one_or_none()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    if permission not in role.permissions:
        role.permissions.append(permission)
        await db.commit()
        await db.refresh(role)
    
    return role

@lru_cache(maxsize=1000)
async def get_role_permissions(db: AsyncSession, role_name: str) -> Set[str]:
    role = await get_role_by_name(db, role_name)
    if not role:
        return set()
    
    permissions = set()
    
    # Dodaj bezpośrednie uprawnienia roli
    for permission in role.permissions:
        permissions.add(f"{permission.resource}:{permission.action}")
    
    # Dodaj uprawnienia z ról nadrzędnych
    for parent_role in role.parent_roles:
        parent_permissions = await get_role_permissions(db, parent_role.name)
        permissions.update(parent_permissions)
    
    return permissions

async def check_permission(db: AsyncSession, user: User, resource: str, action: str) -> bool:
    if user.is_superuser:
        return True
    
    required_permission = f"{resource}:{action}"
    
    for role in user.roles:
        role_permissions = await get_role_permissions(db, role.name)
        if required_permission in role_permissions:
            return True
    
    return False

async def assign_role_to_user(db: AsyncSession, user_id: int, role_name: str):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = await get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role not in user.roles:
        user.roles.append(role)
        await db.commit()
    
    return user

async def remove_role_from_user(db: AsyncSession, user_id: int, role_name: str):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = await get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role in user.roles:
        user.roles.remove(role)
        await db.commit()
    
    return user 