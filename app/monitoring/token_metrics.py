from prometheus_client import Counter, Histogram, Gauge, Summary
from datetime import datetime
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import sys

logger = logging.getLogger(__name__)

# Metryki dla tokenów
TOKEN_OPERATIONS = Counter(
    'token_operations_total',
    'Total number of token operations',
    ['operation', 'status']
)

TOKEN_VALIDATION_TIME = Histogram(
    'token_validation_seconds',
    'Time spent validating tokens',
    ['token_type']
)

ACTIVE_TOKENS = Gauge(
    'active_tokens_total',
    'Number of active tokens',
    ['token_type']
)

REVOKED_TOKENS = Counter(
    'revoked_tokens_total',
    'Number of revoked tokens'
)

# Dodanie nowych metryk
TOKEN_CACHE_OPERATIONS = Counter(
    'token_cache_operations_total',
    'Total number of token cache operations',
    ['operation', 'status']
)

TOKEN_CLEANUP_DURATION = Summary(
    'token_cleanup_duration_seconds',
    'Time spent cleaning up tokens'
)

TOKEN_CACHE_SIZE = Gauge(
    'token_cache_size_bytes',
    'Size of token cache in bytes'
)

async def _update_performance_metrics(db: AsyncSession):
    """Aktualizuje metryki wydajności tokenów."""
    try:
        # Przykładowa implementacja - dostosuj do swoich potrzeb
        TOKEN_CACHE_SIZE.set(sys.getsizeof(db))
    except Exception as e:
        logger.error(f"Błąd aktualizacji metryk wydajności: {str(e)}")

async def _update_cache_metrics():
    """Aktualizuje metryki cache'a tokenów."""
    try:
        # Przykładowa implementacja - dostosuj do swoich potrzeb
        TOKEN_CACHE_OPERATIONS.labels(operation="check", status="success").inc()
    except Exception as e:
        logger.error(f"Błąd aktualizacji metryk cache: {str(e)}")

async def update_token_metrics(db: AsyncSession):
    """Aktualizuje rozszerzone metryki tokenów."""
    try:
        with TOKEN_CLEANUP_DURATION.time():
            # Dodanie nowych metryk wydajności
            await _update_performance_metrics(db)
            await _update_cache_metrics()
    except Exception as e:
        logger.error(f"Błąd aktualizacji metryk: {str(e)}") 