from datetime import datetime, timedelta
from sqlalchemy import delete, and_, func
from app.models.token import RevokedToken, PasswordResetToken
from app.db.database import async_session
from app.monitoring.db_metrics import monitor_db_operation
from app.monitoring.token_metrics import TOKEN_OPERATIONS
from app.core.cache import redis_cache
import logging
import asyncio

logger = logging.getLogger(__name__)

class TokenCleanupService:
    def __init__(self):
        self._batch_size = 1000
        self._cleanup_lock = asyncio.Lock()
        self._cache = redis_cache

    @monitor_db_operation("cleanup_tokens")
    async def cleanup_expired_tokens(self):
        """Czyści tokeny z wykorzystaniem blokady i cache."""
        if not await self._cleanup_lock.acquire(blocking=False):
            logger.info("Czyszczenie tokenów już trwa")
            return

        try:
            async with async_session() as session:
                total_deleted = await self._cleanup_tokens(session)
                await self._update_cache()
                TOKEN_OPERATIONS.labels(operation="cleanup", status="success").inc()
                logger.info(f"Wyczyszczono {total_deleted} tokenów")
        except Exception as e:
            TOKEN_OPERATIONS.labels(operation="cleanup", status="error").inc()
            logger.error(f"Błąd podczas czyszczenia tokenów: {str(e)}")
            raise
        finally:
            self._cleanup_lock.release()

cleanup_service = TokenCleanupService() 