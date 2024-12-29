import pytest
from unittest.mock import patch, AsyncMock
from app.services.auth_service import AuthService
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import authenticate_user
from app.models.errors import ErrorMessages
from datetime import datetime, timedelta
from jose import jwt, JWTError as InvalidTokenError, ExpiredSignatureError as TokenExpiredError
import sys
from pathlib import Path

# Dodanie ścieżki do katalogu głównego projektu
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from tests.fixtures.users import test_users, login_test_cases
from tests.fixtures.tokens import test_tokens, token_validation_test_cases

@pytest.fixture
def auth_service():
    return AuthService()

@pytest.fixture
def mock_user_data():
    return test_users[1]  # używamy regularnego użytkownika z fixtures

@pytest.fixture
def mock_user(mock_user_data):
    user = User()
    user.email = mock_user_data["email"]
    user.username = mock_user_data["username"]
    user.hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKxcQw8.OzLMHCa"
    user.is_active = mock_user_data["is_active"]
    user.is_superuser = mock_user_data["is_superuser"]
    return user

@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service, mock_user_data, mock_user, mock_db):
    """Test udanej autentykacji użytkownika."""
    with patch('app.services.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        user = await authenticate_user(
            mock_db,
            mock_user_data["email"],
            mock_user_data["password"]
        )
        assert user is not None
        assert user.email == mock_user_data["email"]
        assert user.is_active == mock_user_data["is_active"]
        mock_get_user.assert_called_once_with(mock_db, mock_user_data["email"])

@pytest.mark.asyncio
async def test_authenticate_inactive_user(auth_service, mock_db):
    """Test próby logowania nieaktywnego użytkownika."""
    inactive_user = User()
    inactive_user.email = test_users[2]["email"]  # Używamy danych nieaktywnego użytkownika
    inactive_user.is_active = False
    
    with patch('app.services.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = inactive_user
        
        result = await authenticate_user(
            mock_db,
            inactive_user.email,
            test_users[2]["password"]
        )
        
        assert result is None
        error = await auth_service.get_last_error()
        assert error == ErrorMessages.INACTIVE_USER

@pytest.mark.asyncio
async def test_token_creation_and_validation(auth_service):
    """Test tworzenia i walidacji tokenów z różnymi uprawnieniami."""
    for token_data in test_tokens:
        token = auth_service.create_access_token(
            data={"sub": token_data["email"], "scopes": token_data["scopes"]},
            expires_delta=timedelta(minutes=30)
        )
        
        if token_data["exp"] > datetime.utcnow():
            decoded = auth_service.decode_token(token)
            assert decoded["sub"] == token_data["email"]
            assert decoded["scopes"] == token_data["scopes"]
        else:
            with pytest.raises(TokenExpiredError):
                auth_service.decode_token(token)

@pytest.mark.asyncio
async def test_token_validation_cases(auth_service):
    """Test różnych przypadków walidacji tokenów."""
    for case in token_validation_test_cases:
        token = case["token"]
        if case["should_be_valid"]:
            try:
                result = await auth_service.validate_token(token)
                assert result is not None
            except (InvalidTokenError, TokenExpiredError):
                pytest.fail(f"Token powinien być ważny: {case['description']}")
        else:
            with pytest.raises((InvalidTokenError, TokenExpiredError)):
                await auth_service.validate_token(token)

@pytest.mark.asyncio
async def test_rate_limiting(auth_service, mock_db):
    """Test limitowania prób logowania."""
    max_attempts = 5
    auth_service.set_rate_limit(max_attempts, timedelta(minutes=15))
    
    user_email = test_users[0]["email"]
    
    # Symulacja wielokrotnych prób logowania
    for i in range(max_attempts + 1):
        result = await auth_service.check_rate_limit(user_email)
        if i < max_attempts:
            assert result is True
        else:
            assert result is False
            error = await auth_service.get_last_error()
            assert error == ErrorMessages.TOO_MANY_ATTEMPTS

@pytest.mark.asyncio
async def test_password_reset_flow(auth_service, mock_db, mock_user):
    """Test pełnego procesu resetowania hasła."""
    # Generowanie tokenu resetowania hasła
    reset_token = await auth_service.create_password_reset_token(mock_user.email)
    assert reset_token is not None
    
    # Walidacja tokenu
    is_valid = await auth_service.verify_password_reset_token(reset_token)
    assert is_valid is True
    
    # Zmiana hasła
    new_password = "NewSecurePass123!@#"
    success = await auth_service.reset_password(reset_token, new_password)
    assert success is True
    
    # Próba użycia wykorzystanego tokenu
    with pytest.raises(InvalidTokenError):
        await auth_service.reset_password(reset_token, "AnotherPass123!@#")

@pytest.mark.asyncio
async def test_session_management(auth_service, mock_user):
    """Test zarządzania sesjami użytkownika."""
    # Utworzenie sesji
    session_token = await auth_service.create_session(mock_user)
    assert session_token is not None
    
    # Walidacja sesji
    session = await auth_service.validate_session(session_token)
    assert session is not None
    assert session.user_id == mock_user.id
    
    # Zakończenie sesji
    await auth_service.end_session(session_token)
    
    # Próba użycia zakończonej sesji
    with pytest.raises(InvalidTokenError):
        await auth_service.validate_session(session_token) 