import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.database import Base
from app.main import app
from app.db.init_db import init_db
import os
from sqlalchemy.sql import text
import logging
import sys
from pathlib import Path

# Dodanie ścieżki do katalogu głównego projektu
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

pytest_plugins = ('pytest_asyncio',)

# Konfiguracja pytest-asyncio
pytestmark = pytest.mark.asyncio

# Konfiguracja bazy danych testowej
TEST_SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@db:5432/test_db"
)

engine = create_async_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    echo=False,
    future=True
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session", autouse=True)
async def create_test_database():
    """Tworzy i inicjalizuje bazę danych testową."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        await init_db(session)
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def test_db_setup():
    """Czyści dane przed każdym testem."""
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        async with session.begin():
            yield session

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client using the specified event loop."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Test123!@#",
        "full_name": "Test User"
    } 

@pytest.fixture
def mock_captcha(monkeypatch):
    """Mock dla weryfikacji CAPTCHA."""
    async def mock_verify_captcha(*args, **kwargs):
        return True
    monkeypatch.setattr("app.routes.user_routes.verify_captcha", mock_verify_captcha) 

@pytest.fixture(autouse=True)
async def clean_db(db_session):
    """Czyszczenie sesji po każdym teście."""
    yield
    await db_session.rollback()
    await db_session.close() 

@pytest.fixture
async def transaction():
    """Fixture do zarządzania transakcjami w testach."""
    async with engine.begin() as connection:
        transaction = connection.begin()
        yield
        await transaction.rollback() 

@pytest.fixture(scope="session", autouse=True)
async def cleanup_database():
    """Czyści bazę danych po każdym teście."""
    async with engine.begin() as conn:
        # Wyłącz sprawdzanie kluczy obcych
        await conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        
        # Usuń dane ze wszystkich tabel
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        
        # Zresetuj sekwencje
        for table in Base.metadata.sorted_tables:
            if any(column.autoincrement for column in table.columns):
                await conn.execute(
                    text(f"ALTER SEQUENCE {table.name}_id_seq RESTART WITH 1")
                )
        
        # Włącz z powrotem sprawdzanie kluczy obcych
        await conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

@pytest.fixture(autouse=True)
async def ensure_roles(db_session):
    """Upewnia się, że role są zainicjalizowane przed testami."""
    from app.main import init_roles
    try:
        await init_roles()
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise 

@pytest.fixture(scope="function")
async def test_transaction():
    """Zapewnia izolację transakcji dla każdego testu."""
    connection = await engine.connect()
    transaction = await connection.begin()
    
    # Zagnieżdżona transakcja dla każdego testu
    nested = await connection.begin_nested()
    
    # Przekazanie połączenia do sesji
    session_factory = sessionmaker(
        connection, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await nested.rollback()
        await transaction.rollback()
        await connection.close() 

@pytest.fixture(autouse=True)
async def reset_sequences(db_session):
    """Reset sekwencji ID po każdym teście."""
    async with db_session.begin():
        for table in Base.metadata.sorted_tables:
            if any(column.autoincrement for column in table.columns):
                await db_session.execute(
                    text(f"ALTER SEQUENCE {table.name}_id_seq RESTART WITH 1")
                ) 

@pytest.fixture(autouse=True)
def setup_logging():
    """Konfiguracja logowania dla testów."""
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('sqlalchemy.engine')
    logger.setLevel(logging.INFO)
    
    def log_sql(sql):
        logger.info(f"Executing SQL: {sql}")
    
    engine.echo = True
    engine.logger = log_sql 