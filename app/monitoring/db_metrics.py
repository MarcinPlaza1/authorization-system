from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps
import psutil
import logging

logger = logging.getLogger(__name__)

# Metryki Prometheus
DB_OPERATION_DURATION = Histogram(
    'db_operation_duration_seconds',
    'Duration of database operations',
    ['operation_type', 'status']
)

DB_ERRORS = Counter(
    'db_errors_total',
    'Total count of database errors',
    ['error_type', 'operation']
)

DB_CONNECTIONS = Gauge(
    'db_connections_current',
    'Current number of database connections'
)

DB_POOL_SIZE = Gauge(
    'db_pool_size_current',
    'Current database connection pool size'
)

def monitor_db_operation(operation_type: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                DB_ERRORS.labels(
                    error_type=type(e).__name__,
                    operation=operation_type
                ).inc()
                logger.error(f"DB Error in {operation_type}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                DB_OPERATION_DURATION.labels(
                    operation_type=operation_type,
                    status=status
                ).observe(duration)
        return wrapper
    return decorator

async def update_db_metrics(engine):
    """Aktualizuje metryki połączeń DB."""
    try:
        pool = engine.pool
        DB_CONNECTIONS.set(pool.size())
        DB_POOL_SIZE.set(pool.maxsize)
    except Exception as e:
        logger.error(f"Error updating DB metrics: {str(e)}") 