from typing import Any, Optional
from datetime import datetime, timedelta
import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

    async def set(self, key: str, value: Any, expires_in: Optional[int] = None) -> None:
        """Zapisuje wartość w Redis z opcjonalnym czasem wygaśnięcia (w sekundach)."""
        try:
            self._redis.set(key, str(value), ex=expires_in)
        except redis.RedisError as e:
            logger.error(f"Błąd podczas zapisywania do Redis: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """Pobiera wartość z Redis."""
        try:
            value = self._redis.get(key)
            return value
        except redis.RedisError as e:
            logger.error(f"Błąd podczas odczytu z Redis: {e}")
            return None

    async def delete(self, key: str) -> None:
        """Usuwa wartość z Redis."""
        try:
            self._redis.delete(key)
        except redis.RedisError as e:
            logger.error(f"Błąd podczas usuwania z Redis: {e}")

    async def clear(self) -> None:
        """Czyści całą bazę Redis."""
        try:
            self._redis.flushdb()
        except redis.RedisError as e:
            logger.error(f"Błąd podczas czyszczenia Redis: {e}")

# Globalna instancja Redis cache
redis_cache = RedisCache()

class Cache:
    def __init__(self):
        self._cache = {}
        self._expiry = {}

    async def set(self, key: str, value: Any, expires_in: Optional[int] = None) -> None:
        """Zapisuje wartość w cache z opcjonalnym czasem wygaśnięcia (w sekundach)."""
        self._cache[key] = value
        if expires_in:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=expires_in)

    async def get(self, key: str) -> Optional[Any]:
        """Pobiera wartość z cache, uwzględniając czas wygaśnięcia."""
        if key not in self._cache:
            return None

        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            await self.delete(key)
            return None

        return self._cache[key]

    async def delete(self, key: str) -> None:
        """Usuwa wartość z cache."""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)

    async def clear(self) -> None:
        """Czyści cały cache."""
        self._cache.clear()
        self._expiry.clear()

    async def cleanup_expired(self) -> None:
        """Usuwa wygasłe wpisy z cache."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self._expiry.items()
            if now > expiry
        ]
        for key in expired_keys:
            await self.delete(key)

# Globalna instancja cache w pamięci
cache = Cache() 