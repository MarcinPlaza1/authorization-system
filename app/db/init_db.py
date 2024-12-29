from sqlalchemy.ext.asyncio import AsyncSession
from app.services.role_service import create_role, get_role_by_name
from app.models.user import Base, Permission, Role, User
from sqlalchemy.exc import IntegrityError
from app.core.security import get_password_hash

async def init_roles(db: AsyncSession):
    """Inicjalizuje domyślne role w systemie."""
    default_roles = [
        ("user", "Standardowy użytkownik systemu"),
        ("admin", "Administrator systemu"),
        ("moderator", "Moderator systemu")
    ]
    
    for role_name, description in default_roles:
        if not await get_role_by_name(db, role_name):
            await create_role(db, role_name, description)

async def init_permissions(db: AsyncSession):
    """Inicjalizuje domyślne uprawnienia w systemie."""
    default_permissions = [
        ("read", "Prawo do odczytu"),
        ("write", "Prawo do zapisu"),
        ("delete", "Prawo do usuwania"),
        ("admin", "Pełne uprawnienia administracyjne")
    ]
    
    for name, description in default_permissions:
        try:
            permission = Permission(name=name, description=description)
            db.add(permission)
            await db.commit()
        except IntegrityError:
            await db.rollback()

async def init_admin_user(db: AsyncSession):
    """Inicjalizuje użytkownika administratora."""
    admin_role = await get_role_by_name(db, "admin")
    if admin_role:
        try:
            admin_user = User(
                email="admin@example.com",
                username="admin",
                full_name="System Administrator",
                hashed_password=get_password_hash("admin123!@#"),
                is_active=True,
                is_superuser=True,
                role_id=admin_role.id
            )
            db.add(admin_user)
            await db.commit()
        except IntegrityError:
            await db.rollback()

async def init_db(db: AsyncSession):
    """Inicjalizuje bazę danych."""
    # Inicjalizacja ról
    await init_roles(db)
    
    # Inicjalizacja uprawnień
    await init_permissions(db)
    
    # Inicjalizacja administratora
    await init_admin_user(db) 