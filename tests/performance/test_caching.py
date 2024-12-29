import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import time
import asyncio
from unittest.mock import patch, AsyncMock
from app.core.cache import RedisCache
from typing import Dict, Any

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def redis_mock():
    """Mock dla Redis."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.exists = AsyncMock(return_value=False)
    return cache

async def test_cache_hit_performance(
    client: AsyncClient,
    redis_mock: AsyncMock
):
    """Test wydajności przy trafieniu w cache."""
    cached_data = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }
    redis_mock.get.return_value = cached_data
    
    with patch('app.core.cache.redis', redis_mock):
        start_time = time.time()
        response = await client.get("/api/users/1")
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response.json() == cached_data
        assert response_time < 0.1  # Odpowiedź z cache powinna być szybka
        redis_mock.get.assert_called_once()
        redis_mock.set.assert_not_called()

async def test_cache_miss_behavior(
    client: AsyncClient,
    redis_mock: AsyncMock,
    clean_database: AsyncSession
):
    """Test zachowania przy braku w cache."""
    redis_mock.get.return_value = None
    
    with patch('app.core.cache.redis', redis_mock):
        response = await client.get("/api/users/1")
        
        if response.status_code == 200:
            # Dane powinny zostać zapisane w cache
            redis_mock.set.assert_called_once()
            cache_key = redis_mock.set.call_args[0][0]
            assert "user:1" in cache_key
        else:
            assert response.status_code == 404
            redis_mock.set.assert_not_called()

async def test_cache_invalidation(
    client: AsyncClient,
    redis_mock: AsyncMock,
    test_user_data: dict
):
    """Test unieważniania cache."""
    # Utworzenie użytkownika
    response = await client.post("/api/users/", json=test_user_data)
    assert response.status_code == 201
    user_id = response.json()["id"]
    
    with patch('app.core.cache.redis', redis_mock):
        # Aktualizacja użytkownika
        update_data = {"full_name": "Updated Name"}
        response = await client.patch(
            f"/api/users/{user_id}",
            json=update_data
        )
        assert response.status_code == 200
        
        # Cache powinien zostać unieważniony
        redis_mock.delete.assert_called()
        cache_key = redis_mock.delete.call_args[0][0]
        assert f"user:{user_id}" in cache_key

async def test_cache_ttl(
    client: AsyncClient,
    redis_mock: AsyncMock
):
    """Test czasu życia cache."""
    with patch('app.core.cache.redis', redis_mock):
        response = await client.get("/api/users/1")
        
        if response.status_code == 200:
            # Sprawdzenie czy ustawiono TTL
            redis_mock.set.assert_called_once()
            _, ttl = redis_mock.set.call_args[0][1:3]
            assert isinstance(ttl, int)
            assert ttl > 0

async def test_cache_race_condition(
    client: AsyncClient,
    redis_mock: AsyncMock,
    clean_database: AsyncSession
):
    """Test wyścigu przy równoczesnym dostępie do cache."""
    async def simulate_request():
        return await client.get("/api/users/1")
    
    with patch('app.core.cache.redis', redis_mock):
        # Symulacja równoczesnych żądań
        tasks = [simulate_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # Wszystkie odpowiedzi powinny być spójne
        first_response = responses[0].json() if responses[0].status_code == 200 else None
        for response in responses[1:]:
            if response.status_code == 200:
                assert response.json() == first_response

async def test_cache_pattern_invalidation(
    client: AsyncClient,
    redis_mock: AsyncMock,
    test_user_data: dict
):
    """Test unieważniania cache według wzorca."""
    with patch('app.core.cache.redis', redis_mock):
        # Utworzenie użytkownika
        response = await client.post("/api/users/", json=test_user_data)
        user_id = response.json()["id"]
        
        # Pobranie listy użytkowników (cache)
        await client.get("/api/users")
        
        # Aktualizacja użytkownika
        await client.patch(
            f"/api/users/{user_id}",
            json={"full_name": "New Name"}
        )
        
        # Sprawdzenie czy unieważniono cache dla wzorca
        pattern = "users:list:*"
        redis_mock.delete.assert_any_call(pattern)

async def test_conditional_caching(
    client: AsyncClient,
    redis_mock: AsyncMock
):
    """Test warunkowego cachowania."""
    headers = {"Cache-Control": "no-cache"}
    
    with patch('app.core.cache.redis', redis_mock):
        # Żądanie z no-cache
        response = await client.get("/api/users/1", headers=headers)
        redis_mock.get.assert_not_called()
        
        # Żądanie bez no-cache
        response = await client.get("/api/users/1")
        redis_mock.get.assert_called_once()

async def test_cache_stampede_prevention(
    client: AsyncClient,
    redis_mock: AsyncMock
):
    """Test zapobiegania cache stampede."""
    def simulate_slow_db_query(*args, **kwargs):
        time.sleep(0.5)
        return {"id": 1, "username": "test"}
    
    with patch('app.services.user_service.get_user_by_id', side_effect=simulate_slow_db_query), \
         patch('app.core.cache.redis', redis_mock):
        # Symulacja wielu równoczesnych żądań podczas wygaśnięcia cache
        tasks = [client.get("/api/users/1") for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # Tylko jedno żądanie powinno trafić do bazy
        assert redis_mock.set.call_count == 1

async def test_cache_size_limit(
    client: AsyncClient,
    redis_mock: AsyncMock,
    clean_database: AsyncSession
):
    """Test limitu rozmiaru cache."""
    # Generowanie dużej ilości danych
    large_data = "x" * 1024 * 1024  # 1MB
    
    with patch('app.core.cache.redis', redis_mock):
        response = await client.post("/api/users/", json={
            "username": "test",
            "email": "test@example.com",
            "password": "Test123!@#",
            "full_name": large_data
        })
        
        assert response.status_code == 201
        # Cache nie powinien być użyty dla zbyt dużych obiektów
        redis_mock.set.assert_not_called() 