import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.rate_limiter import RateLimiter
from app.services.token_service import TokenService
from app.models.user import User
from datetime import datetime, timedelta
from jose import jwt

@pytest.fixture
def mock_redis():
    """Mock dla Redis."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis

@pytest.fixture
def mock_user():
    """Fixture dla użytkownika testowego."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        full_name="Test User"
    )

class TestSecurity:
    """Testy funkcji bezpieczeństwa."""
    
    def test_password_hashing(self):
        """Test hashowania hasła."""
        password = "TestPass123!@#"
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)
    
    def test_access_token_creation(self):
        """Test tworzenia tokenu dostępu."""
        user_id = 1
        token = create_access_token(user_id)
        assert isinstance(token, str)
        decoded = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        assert decoded["sub"] == str(user_id)

class TestRateLimiter:
    """Testy izolowane dla rate limitera."""
    
    async def test_rate_limiting_basic(self, rate_limiter, mock_redis):
        """Test podstawowego limitowania żądań."""
        with patch('app.core.rate_limiter.redis', mock_redis):
            client_ip = "127.0.0.1"
            assert await rate_limiter.check_rate_limit(client_ip)
            mock_redis.incr.return_value = rate_limiter.max_requests + 1
            assert not await rate_limiter.check_rate_limit(client_ip)
    
    async def test_blocking_mechanism(self, rate_limiter, mock_redis):
        """Test mechanizmu blokowania."""
        with patch('app.core.rate_limiter.redis', mock_redis):
            client_ip = "127.0.0.1"
            mock_redis.get.return_value = "blocked"
            assert not await rate_limiter.check_rate_limit(client_ip)
            mock_redis.get.return_value = None
            mock_redis.incr.return_value = 1
            assert await rate_limiter.check_rate_limit(client_ip)

class TestTokenService:
    """Testy izolowane dla serwisu tokenów."""
    
    async def test_token_lifecycle(self, token_service, mock_db: AsyncSession, mock_user):
        """Test pełnego cyklu życia tokenu."""
        # Tworzenie tokenu
        token = await token_service.create_access_token(mock_user)
        assert isinstance(token, str)
        decoded = jwt.decode(
            token,
            token_service.secret_key,
            algorithms=[token_service.algorithm]
        )
        assert decoded["sub"] == mock_user.id
        
        # Odświeżanie tokenu
        refresh_token = await token_service.create_refresh_token(mock_user)
        new_token = await token_service.refresh_access_token(refresh_token)
        assert new_token != token
        
        # Blacklisting
        with patch('app.services.token_service.redis', mock_redis):
            await token_service.blacklist_token(token)
            mock_redis.set.assert_called_with(
                f"blacklist:{token}",
                "1",
                ex=token_service.token_expire_minutes * 60
            )
            mock_redis.get.return_value = "1"
            assert await token_service.is_token_blacklisted(token) 