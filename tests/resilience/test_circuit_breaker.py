import pytest
from httpx import AsyncClient, NetworkError
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from app.core.circuit_breaker import CircuitBreaker
from app.core.retry import RetryStrategy
import asyncio
import time

pytestmark = pytest.mark.asyncio

@pytest.fixture
def circuit_breaker():
    """Fixture dla Circuit Breaker."""
    return CircuitBreaker(
        failure_threshold=3,
        reset_timeout=5,
        half_open_timeout=2
    )

@pytest.fixture
def retry_strategy():
    """Fixture dla strategii ponownych prób."""
    return RetryStrategy(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=2
    )

async def test_circuit_breaker_state_transitions(
    client: AsyncClient,
    circuit_breaker: CircuitBreaker
):
    """Test przejść między stanami Circuit Breaker."""
    with patch('app.core.circuit_breaker.breaker', circuit_breaker):
        # Stan początkowy - zamknięty
        assert circuit_breaker.is_closed()
        
        # Symulacja błędów
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(NetworkError):
                await client.get("/api/external-service")
        
        # Stan po błędach - otwarty
        assert circuit_breaker.is_open()
        
        # Oczekiwanie na przejście do half-open
        await asyncio.sleep(circuit_breaker.half_open_timeout)
        assert circuit_breaker.is_half_open()
        
        # Udane żądanie w stanie half-open
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert circuit_breaker.is_closed()

async def test_retry_with_exponential_backoff(
    client: AsyncClient,
    retry_strategy: RetryStrategy
):
    """Test strategii ponownych prób z wykładniczym opóźnieniem."""
    mock_service = AsyncMock()
    mock_service.side_effect = [
        NetworkError("Connection failed"),
        NetworkError("Connection failed"),
        {"status": "success"}
    ]
    
    start_time = time.time()
    
    with patch('app.services.external_service.call', mock_service):
        response = await client.get("/api/external-service")
        
        total_time = time.time() - start_time
        expected_min_time = sum([
            retry_strategy.initial_delay * (retry_strategy.exponential_base ** i)
            for i in range(2)  # 2 retry'e
        ])
        
        assert response.status_code == 200
        assert total_time >= expected_min_time
        assert mock_service.call_count == 3

async def test_circuit_breaker_with_retry(
    client: AsyncClient,
    circuit_breaker: CircuitBreaker,
    retry_strategy: RetryStrategy
):
    """Test integracji Circuit Breaker z mechanizmem retry."""
    with patch('app.core.circuit_breaker.breaker', circuit_breaker), \
         patch('app.core.retry.strategy', retry_strategy):
        
        # Symulacja serii błędów
        for _ in range(2):  # Mniej niż próg circuit breakera
            with pytest.raises(NetworkError):
                await client.get("/api/external-service")
        
        assert circuit_breaker.is_closed()  # Wciąż zamknięty
        
        # Kolejne błędy z retry
        mock_service = AsyncMock()
        mock_service.side_effect = [
            NetworkError("Connection failed"),
            NetworkError("Connection failed"),
            NetworkError("Connection failed")
        ]
        
        with patch('app.services.external_service.call', mock_service):
            with pytest.raises(NetworkError):
                await client.get("/api/external-service")
            
            assert circuit_breaker.is_open()  # Teraz otwarty
            assert mock_service.call_count <= retry_strategy.max_retries

async def test_concurrent_circuit_breaker(
    client: AsyncClient,
    circuit_breaker: CircuitBreaker
):
    """Test zachowania Circuit Breaker przy równoczesnych żądaniach."""
    with patch('app.core.circuit_breaker.breaker', circuit_breaker):
        # Symulacja wielu równoczesnych błędów
        async def make_request():
            try:
                return await client.get("/api/external-service")
            except NetworkError:
                return None
        
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # Circuit Breaker powinien się otworzyć po przekroczeniu progu
        assert circuit_breaker.is_open()
        assert responses.count(None) >= circuit_breaker.failure_threshold

async def test_retry_timeout(
    client: AsyncClient,
    retry_strategy: RetryStrategy
):
    """Test timeout'u dla mechanizmu retry."""
    slow_response = AsyncMock()
    slow_response.side_effect = lambda: asyncio.sleep(2)
    
    with patch('app.services.external_service.call', slow_response), \
         patch('app.core.retry.strategy', retry_strategy):
        
        start_time = time.time()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                client.get("/api/external-service"),
                timeout=1.0
            )
        
        total_time = time.time() - start_time
        assert total_time < retry_strategy.max_delay * retry_strategy.max_retries

async def test_circuit_breaker_metrics(
    client: AsyncClient,
    circuit_breaker: CircuitBreaker
):
    """Test metryk Circuit Breaker."""
    with patch('app.core.circuit_breaker.breaker', circuit_breaker):
        # Udane żądanie
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert circuit_breaker.success_count == 1
        assert circuit_breaker.failure_count == 0
        
        # Nieudane żądania
        for _ in range(2):
            with pytest.raises(NetworkError):
                await client.get("/api/external-service")
        
        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.error_rate == 2/3  # 2 błędy na 3 żądania

async def test_retry_jitter(
    client: AsyncClient,
    retry_strategy: RetryStrategy
):
    """Test losowego rozrzutu czasów retry."""
    delays = []
    
    async def mock_call_with_delay():
        start = time.time()
        await retry_strategy.wait_before_retry(len(delays))
        delays.append(time.time() - start)
        raise NetworkError("Connection failed")
    
    with patch('app.services.external_service.call', mock_call_with_delay):
        with pytest.raises(NetworkError):
            await client.get("/api/external-service")
    
    # Sprawdzenie czy opóźnienia nie są dokładnie wykładnicze
    for i in range(1, len(delays)):
        expected = retry_strategy.initial_delay * (retry_strategy.exponential_base ** i)
        assert abs(delays[i] - expected) > 0  # Powinno być różne od dokładnej wartości

async def test_circuit_breaker_recovery(
    client: AsyncClient,
    circuit_breaker: CircuitBreaker
):
    """Test odzyskiwania po otwarciu Circuit Breaker."""
    with patch('app.core.circuit_breaker.breaker', circuit_breaker):
        # Otwarcie circuit breakera
        for _ in range(circuit_breaker.failure_threshold):
            with pytest.raises(NetworkError):
                await client.get("/api/external-service")
        
        assert circuit_breaker.is_open()
        
        # Oczekiwanie na reset
        await asyncio.sleep(circuit_breaker.reset_timeout)
        
        # Próba odzyskania
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert circuit_breaker.is_closed()
        
        # Sprawdzenie czy liczniki zostały zresetowane
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 1 