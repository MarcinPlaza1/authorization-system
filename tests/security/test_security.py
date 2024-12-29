import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
import re
from typing import List
from app.core.security import SecurityService

pytestmark = pytest.mark.asyncio

@pytest.fixture
def security_service():
    """Fixture dostarczający serwis bezpieczeństwa."""
    return SecurityService()

@pytest.fixture
def malicious_payloads() -> List[str]:
    """Przykładowe złośliwe payloady."""
    return [
        "<script>alert('xss')</script>",
        "' OR '1'='1",
        "admin'--",
        "1; DROP TABLE users--",
        "' UNION SELECT * FROM users--",
        "${7*7}",
        "{{7*7}}"
    ]

async def test_password_validation(security_service):
    """Test walidacji haseł."""
    # Poprawne hasło
    assert security_service.validate_password_complexity("Test123!@#")
    
    # Niepoprawne hasła
    assert not security_service.validate_password_complexity("test")  # Za krótkie
    assert not security_service.validate_password_complexity("testtest")  # Brak wielkich liter i cyfr
    assert not security_service.validate_password_complexity("Test123")  # Brak znaków specjalnych

async def test_token_validation(security_service):
    """Test walidacji tokenów."""
    # Tworzenie tokenu
    test_data = {"user_id": 123, "role": "user"}
    token = security_service.create_token(test_data)
    
    # Walidacja tokenu
    payload = security_service.validate_token(token)
    assert payload.get("user_id") == 123
    assert payload.get("role") == "user"

async def test_password_reset_token(security_service):
    """Test tokenów resetowania hasła."""
    user_id = 123
    token = security_service.create_password_reset_token(user_id)
    validated_user_id = security_service.validate_password_reset_token(token)
    assert validated_user_id == user_id

async def test_input_sanitization(client: AsyncClient, malicious_payloads):
    """Test sanityzacji danych wejściowych."""
    for payload in malicious_payloads:
        response = await client.post(
            "/api/auth/register",
            json={"username": payload, "password": "Test123!@#"}
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

async def test_rate_limiting(client: AsyncClient):
    """Test limitowania liczby żądań."""
    for _ in range(10):
        await client.post(
            "/api/auth/login",
            json={"username": "test", "password": "test"}
        )
    
    response = await client.post(
        "/api/auth/login",
        json={"username": "test", "password": "test"}
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS 