from fastapi import FastAPI, HTTPException, Response
from contextlib import asynccontextmanager
from app.routes import user_routes, admin_routes
from app.db.database import init_db
from app.middleware.security import setup_security_middleware, setup_rate_limiting
from app.middleware.performance import (
    setup_performance_middleware,
    PerformanceMiddleware,
    CacheControlMiddleware
)
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from app.services.role_service import create_role
from app.db.database import AsyncSessionLocal
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

async def init_roles():
    """Inicjalizacja podstawowych ról w systemie."""
    async with AsyncSessionLocal() as db:
        for role_data in [
            {"name": "admin", "description": "Administrator systemu"},
            {"name": "user", "description": "Standardowy użytkownik"},
            {"name": "moderator", "description": "Moderator treści"},
        ]:
            try:
                await create_role(db, **role_data)
                logger.info(f"Utworzono rolę: {role_data['name']}")
            except (IntegrityError, HTTPException) as e:
                logger.info(f"Rola {role_data['name']} już istnieje")
                continue
            except Exception as e:
                logger.error(f"Błąd podczas tworzenia roli {role_data['name']}: {str(e)}")
                raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Konfiguracja aplikacji podczas startu i zamykania."""
    try:
        await init_db()
        await init_roles()
        logger.info("Aplikacja została pomyślnie zainicjalizowana")
        yield
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji aplikacji: {str(e)}")
        raise
    finally:
        logger.info("Zamykanie aplikacji")

app = FastAPI(
    title="FastAPI Project",
    description="A FastAPI project with full structure",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
    openapi_tags=[
        {"name": "users", "description": "Operacje na użytkownikach"},
        {"name": "admin", "description": "Operacje administracyjne"},
    ]
)

# Konfiguracja zabezpieczeń
setup_security_middleware(app)
setup_rate_limiting(app)

# Konfiguracja wydajności
app.add_middleware(
    PerformanceMiddleware,
    slow_request_threshold=1.0,
    max_memory_percent=90.0,
    max_cpu_percent=80.0
)
app.add_middleware(CacheControlMiddleware)

# Dodaj routery
app.include_router(user_routes.router, prefix="/api/users", tags=["users"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])

@app.get("/metrics")
async def metrics():
    """Endpoint dla metryk Prometheus."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Błąd podczas pobierania metryk"
        ) 