import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.user import User
from app.services.auth_service import create_access_token
from app.core.exceptions import ConcurrencyError
from app.services.user_service import get_user_by_email
from typing import List

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def clean_database(db_session: AsyncSession):
    """Czyści bazę danych przed testami."""
    try:
        await db_session.execute(text("TRUNCATE TABLE users CASCADE"))
        await db_session.execute(text("TRUNCATE TABLE tokens CASCADE"))
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        pytest.fail(f"Nie udało się wyczyścić bazy danych: {str(e)}")
    yield db_session

@pytest.fixture
def concurrent_user_data():
    return [
        {
            "email": f"user{i}@example.com",
            "username": f"user{i}",
            "password": "Test123!@#",
            "full_name": f"Test User {i}"
        }
        for i in range(5)
    ]

async def verify_user_registration(
    db_session: AsyncSession,
    email: str,
    expected_status: bool = True
) -> bool:
    """Sprawdza czy użytkownik został prawidłowo zarejestrowany."""
    user = await get_user_by_email(db_session, email)
    return (user is not None) == expected_status

async def test_concurrent_user_registration(
    client: AsyncClient,
    concurrent_user_data: list,
    clean_database: AsyncSession
):
    """Test równoczesnej rejestracji użytkowników."""
    try:
        tasks = [
            client.post("/api/users/", json=user_data)
            for user_data in concurrent_user_data
        ]
        responses = await asyncio.gather(*tasks)
        
        # Sprawdzenie statusów odpowiedzi
        assert all(response.status_code == 201 for response in responses)
        
        # Sprawdzenie unikalności ID
        user_ids = [response.json()["id"] for response in responses]
        assert len(set(user_ids)) == len(responses)
        
        # Sprawdzenie czy użytkownicy są w bazie
        for user_data in concurrent_user_data:
            assert await verify_user_registration(clean_database, user_data["email"])
            
        # Sprawdzenie czy role zostały przypisane
        for response in responses:
            assert "roles" in response.json()
            assert len(response.json()["roles"]) > 0
            
    except Exception as e:
        pytest.fail(f"Test nie powiódł się: {str(e)}")

async def test_concurrent_login_attempts(
    client: AsyncClient,
    test_user_data: dict,
    clean_database: AsyncSession
):
    """Test równoczesnych prób logowania."""
    try:
        # Rejestracja użytkownika
        register_response = await client.post("/api/users/", json=test_user_data)
        assert register_response.status_code == 201
        
        # Próba równoczesnego logowania
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        tasks = [
            client.post("/api/users/token", data=login_data)
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Sprawdzenie odpowiedzi
        assert all(response.status_code == 200 for response in responses)
        
        # Sprawdzenie unikalności tokenów
        tokens = [response.json()["access_token"] for response in responses]
        assert len(set(tokens)) == len(tokens)
        
        # Sprawdzenie czy tokeny są w bazie
        token_count = await clean_database.execute(
            text("SELECT COUNT(*) FROM tokens WHERE user_id = :user_id"),
            {"user_id": register_response.json()["id"]}
        )
        result = await token_count.scalar()
        assert result >= len(tokens)
        
    except ConcurrencyError as e:
        pytest.fail(f"Błąd współbieżności: {str(e)}")
    except Exception as e:
        pytest.fail(f"Test nie powiódł się: {str(e)}")

async def test_concurrent_token_validation(
    client: AsyncClient,
    test_user_data: dict,
    clean_database: AsyncSession
):
    """Test równoczesnej walidacji tokenów."""
    try:
        # Rejestracja użytkownika
        response = await client.post("/api/users/", json=test_user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]
        
        # Generowanie tokenów
        tokens = [
            create_access_token({"sub": user_id})
            for _ in range(5)
        ]
        
        # Równoczesna walidacja
        tasks = [
            client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            for token in tokens
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Sprawdzenie podstawowych asercji
        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["id"] == user_id for response in responses)
        
        # Sprawdzenie szczegółów użytkownika
        for response in responses:
            user_data = response.json()
            assert user_data["email"] == test_user_data["email"]
            assert user_data["username"] == test_user_data["username"]
            assert "roles" in user_data
            
        # Sprawdzenie aktywności tokenów w bazie
        token_count = await clean_database.execute(
            text("SELECT COUNT(*) FROM tokens WHERE user_id = :user_id AND is_active = true"),
            {"user_id": user_id}
        )
        result = await token_count.scalar()
        assert result >= len(tokens)
        
    except Exception as e:
        pytest.fail(f"Test nie powiódł się: {str(e)}")

async def test_concurrent_token_revocation(
    client: AsyncClient,
    test_user_data: dict,
    clean_database: AsyncSession
):
    """Test równoczesnego unieważniania tokenów."""
    try:
        # Rejestracja użytkownika
        response = await client.post("/api/users/", json=test_user_data)
        user_id = response.json()["id"]
        
        # Generowanie i unieważnianie tokenów
        tokens = [create_access_token({"sub": user_id}) for _ in range(3)]
        
        # Równoczesne unieważnianie
        tasks = [
            client.post(
                "/api/users/revoke-token",
                headers={"Authorization": f"Bearer {token}"}
            )
            for token in tokens
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Sprawdzenie odpowiedzi
        assert all(response.status_code == 200 for response in responses)
        
        # Sprawdzenie czy tokeny są unieważnione
        for token in tokens:
            validate_response = await client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert validate_response.status_code == 401
            
    except Exception as e:
        pytest.fail(f"Test nie powiódł się: {str(e)}") 