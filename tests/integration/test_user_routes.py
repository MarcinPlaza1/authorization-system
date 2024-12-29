import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserResponse
from app.services.auth_service import verify_password, get_password_hash, create_access_token
from app.services.role_service import assign_role_to_user
from app.models.errors import ErrorTypes, ErrorMessages
import logging
from app.services.user_service import get_user_by_id
from app.core.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio

@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Test123!@#",
        "full_name": "Test User"
    }

@pytest.fixture
def test_admin_data():
    return {
        "email": "admin@example.com",
        "username": "adminuser",
        "password": "Admin123!@#",
        "full_name": "Admin User"
    }

@pytest.fixture
def weak_password_user_data():
    return {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "weak",
        "full_name": "Weak User"
    }

async def test_register_user_success(client: AsyncClient, test_user_data: dict):
    response = await client.post("/api/users/", json=test_user_data)
    assert response.status_code == 201
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["username"] == test_user_data["username"]
    assert "password" not in data
    assert "roles" in data
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"

async def test_register_user_duplicate_email(
    client: AsyncClient, test_user_data: dict, db_session: AsyncSession
):
    await client.post("/api/users/", json=test_user_data)
    duplicate_user = test_user_data.copy()
    duplicate_user["username"] = "another_user"
    response = await client.post("/api/users/", json=duplicate_user)
    assert response.status_code == 400
    assert response.json()["detail"]["detail"] == "Email jest już zarejestrowany"

async def test_register_user_weak_password(
    client: AsyncClient, weak_password_user_data: dict
):
    response = await client.post("/api/users/", json=weak_password_user_data)
    assert response.status_code == 400
    assert "password" in response.json()["detail"]["detail"].lower()

async def test_register_user_invalid_email(client: AsyncClient, test_user_data: dict):
    invalid_user = test_user_data.copy()
    invalid_user["email"] = "invalid-email"
    response = await client.post("/api/users/", json=invalid_user)
    assert response.status_code == 422

async def test_login_success(client: AsyncClient, test_user_data: dict):
    # Rejestracja użytkownika
    await client.post("/api/users/", json=test_user_data)
    
    # Logowanie
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = await client.post("/api/users/token", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(client: AsyncClient, test_user_data: dict):
    await client.post("/api/users/", json=test_user_data)
    login_data = {
        "username": test_user_data["email"],
        "password": "wrong_password"
    }
    response = await client.post("/api/users/token", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == ErrorMessages.INVALID_CREDENTIALS

async def test_login_nonexistent_user(client: AsyncClient):
    login_data = {
        "username": "nonexistent@example.com",
        "password": "password123"
    }
    response = await client.post("/api/users/token", data=login_data)
    assert response.status_code == 401
    assert "nieprawidłowy email lub hasło" in response.json()["detail"].lower()

async def test_login_attempts_limit(
    client: AsyncClient, test_user_data: dict, db_session: AsyncSession
):
    # Rejestracja użytkownika
    await client.post("/api/users/", json=test_user_data)
    
    # Próba logowania z błędnym hasłem 3 razy
    login_data = {
        "username": test_user_data["email"],
        "password": "wrong_password"
    }
    
    for _ in range(3):
        response = await client.post("/api/users/token", data=login_data)
        assert response.status_code == 401
    
    # Czwarta próba powinna być zablokowana
    response = await client.post("/api/users/token", data=login_data)
    assert response.status_code == 429
    assert "too many attempts" in response.json()["detail"].lower() 

async def test_user_role_assignment(client: AsyncClient, test_user_data: dict, db_session: AsyncSession):
    """Test sprawdzający czy nowy użytkownik otrzymuje rolę 'user'."""
    response = await client.post("/api/users/", json=test_user_data)
    assert response.status_code == 201
    
    user_id = response.json()["id"]
    user = await get_user_by_id(db_session, user_id)
    assert user is not None
    assert len(user.roles) == 1
    assert user.roles[0].name == "user" 