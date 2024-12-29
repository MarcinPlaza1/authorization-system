from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.token import RevokedToken, TokenData
from app.core.cache import redis_cache
from app.monitoring.db_metrics import monitor_db_operation
from app.monitoring.token_metrics import TOKEN_OPERATIONS, TOKEN_VALIDATION_TIME
import uuid
import logging
import asyncio
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1 godzina
BATCH_SIZE = 1000  # Rozmiar partii dla operacji wsadowych

class TokenService:
    def __init__(self):
        self._cache = redis_cache
        self._cleanup_lock = asyncio.Lock()
    
    @monitor_db_operation("revoke_token")
    async def revoke_token(self, db: AsyncSession, token_data: TokenData) -> Tuple[bool, Optional[str]]:
        """Unieważnia token."""
        try:
            revoked_token = RevokedToken(
                jti=token_data.jti,
                expires_at=datetime.utcnow() + timedelta(seconds=token_data.exp)
            )
            db.add(revoked_token)
            await db.commit()
            
            # Aktualizuj cache
            cache_key = f"token_valid:{token_data.jti}"
            await self._cache.set(cache_key, 0, expires_in=CACHE_TTL)
            
            TOKEN_OPERATIONS.labels(operation="revocation", status="success").inc()
            return True, None
        except Exception as e:
            TOKEN_OPERATIONS.labels(operation="revocation", status="error").inc()
            logger.error(f"Błąd unieważniania tokenu: {str(e)}")
            return False, str(e)

    @monitor_db_operation("validate_token")
    async def validate_token(self, db: AsyncSession, token_data: TokenData) -> Tuple[bool, Optional[str]]:
        """Waliduje token z cache i bazą danych."""
        with TOKEN_VALIDATION_TIME.labels(token_type="access").time():
            try:
                # Sprawdź cache
                cache_key = f"token_valid:{token_data.jti}"
                cached_result = await self._cache.get(cache_key)
                
                if cached_result is not None:
                    TOKEN_OPERATIONS.labels(operation="cache_hit", status="success").inc()
                    return bool(int(cached_result)), None
                
                # Sprawdź w bazie
                is_valid = not await self._is_token_revoked(db, token_data)
                await self._cache.set(cache_key, int(is_valid), expire=CACHE_TTL)
                
                TOKEN_OPERATIONS.labels(operation="validation", status="success").inc()
                return is_valid, None
                
            except Exception as e:
                TOKEN_OPERATIONS.labels(operation="validation", status="error").inc()
                logger.error(f"Błąd walidacji tokenu: {str(e)}")
                return False, str(e)

    async def _is_token_revoked(self, db: AsyncSession, token_data: TokenData) -> bool:
        """Sprawdza czy token jest unieważniony."""
        result = await db.execute(
            select(RevokedToken).where(
                and_(
                    RevokedToken.jti == token_data.jti,
                    RevokedToken.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def cleanup_expired_tokens(self):
        """Czyści wygasłe tokeny z wykorzystaniem blokady."""
        if not await self._cleanup_lock.acquire(blocking=False):
            logger.info("Czyszczenie tokenów już trwa")
            return

        try:
            await self._perform_cleanup()
        finally:
            self._cleanup_lock.release()

token_service = TokenService() 