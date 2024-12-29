import pytest
from app.middleware.performance import PerformanceMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient
import time
import psutil

def test_performance_middleware_initialization():
    """Test inicjalizacji middleware z parametrami."""
    middleware = PerformanceMiddleware(
        app=None,
        slow_request_threshold=2.0,
        max_memory_percent=85.0,
        max_cpu_percent=75.0
    )
    assert middleware.slow_request_threshold == 2.0
    assert middleware.max_memory_percent == 85.0
    assert middleware.max_cpu_percent == 75.0

def test_performance_middleware_default_values():
    """Test domyślnych wartości middleware."""
    middleware = PerformanceMiddleware(app=None)
    assert middleware.slow_request_threshold == 1.0
    assert middleware.max_memory_percent == 90.0
    assert middleware.max_cpu_percent == 80.0

@pytest.mark.asyncio
async def test_system_resources_check():
    """Test sprawdzania zasobów systemowych."""
    middleware = PerformanceMiddleware(
        app=None,
        max_memory_percent=100.0,  # Ustawienie wysokiego limitu dla testu
        max_cpu_percent=100.0
    )
    result = await middleware.check_system_resources()
    assert result is True  # Przy wysokich limitach test powinien przejść

@pytest.mark.asyncio
async def test_system_resources_check_memory_limit():
    """Test limitu pamięci."""
    current_memory = psutil.virtual_memory().percent
    middleware = PerformanceMiddleware(
        app=None,
        max_memory_percent=current_memory - 10.0  # Ustawienie limitu poniżej aktualnego użycia
    )
    result = await middleware.check_system_resources()
    assert result is False

def test_performance_middleware_integration():
    """Test integracji middleware z aplikacją FastAPI."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        time.sleep(0.1)  # Symulacja wolnego endpointu
        return {"message": "test"}
    
    app.add_middleware(
        PerformanceMiddleware,
        slow_request_threshold=0.05  # Niski próg dla testu
    )
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    process_time = float(response.headers["X-Process-Time"])
    assert process_time > 0.05  # Sprawdzenie czy czas przetwarzania został zmierzony

def test_performance_middleware_system_overload():
    """Test zachowania middleware przy przeciążeniu systemu."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    app.add_middleware(
        PerformanceMiddleware,
        max_memory_percent=0.0,  # Ustawienie niemożliwego do spełnienia limitu
        max_cpu_percent=0.0
    )
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 503
    assert response.json()["error"]["message"] == "System jest przeciążony. Spróbuj ponownie później." 