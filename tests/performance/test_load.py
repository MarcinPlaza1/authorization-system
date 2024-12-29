import pytest
import asyncio
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import statistics

pytestmark = pytest.mark.asyncio

@pytest.fixture
def load_test_users(number_of_users: int = 100):
    """Generuje dane testowe dla wielu użytkowników."""
    return [
        {
            "email": f"user{i}@loadtest.com",
            "username": f"loaduser{i}",
            "password": "LoadTest123!@#",
            "full_name": f"Load Test User {i}"
        }
        for i in range(number_of_users)
    ]

async def measure_response_time(task) -> float:
    """Mierzy czas odpowiedzi dla zadania."""
    start_time = time.time()
    await task
    return time.time() - start_time

async def test_concurrent_user_registration_performance(
    client: AsyncClient,
    load_test_users: List[dict],
    clean_database: AsyncSession
):
    """Test wydajności równoczesnej rejestracji użytkowników."""
    tasks = [
        client.post("/api/users/", json=user_data)
        for user_data in load_test_users
    ]
    
    # Pomiar czasów odpowiedzi
    response_times = await asyncio.gather(
        *[measure_response_time(task) for task in tasks]
    )
    
    # Analiza wyników
    avg_response_time = statistics.mean(response_times)
    max_response_time = max(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
    
    # Asercje wydajnościowe
    assert avg_response_time < 1.0, f"Średni czas odpowiedzi ({avg_response_time:.2f}s) przekracza 1s"
    assert max_response_time < 2.0, f"Maksymalny czas odpowiedzi ({max_response_time:.2f}s) przekracza 2s"
    assert p95_response_time < 1.5, f"95ty percentyl czasu odpowiedzi ({p95_response_time:.2f}s) przekracza 1.5s"

async def test_concurrent_login_performance(
    client: AsyncClient,
    load_test_users: List[dict],
    clean_database: AsyncSession
):
    """Test wydajności równoczesnego logowania."""
    # Rejestracja użytkowników
    for user_data in load_test_users:
        await client.post("/api/users/", json=user_data)
    
    # Przygotowanie danych logowania
    login_data = [
        {
            "username": user["email"],
            "password": user["password"]
        }
        for user in load_test_users
    ]
    
    # Równoczesne logowanie
    tasks = [
        client.post("/api/users/token", data=data)
        for data in login_data
    ]
    
    start_time = time.time()
    responses = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Sprawdzenie poprawności
    success_count = sum(1 for r in responses if r.status_code == 200)
    success_rate = success_count / len(responses)
    
    # Asercje
    assert success_rate >= 0.95, f"Współczynnik sukcesu ({success_rate:.2%}) poniżej 95%"
    assert total_time < 5.0, f"Całkowity czas wykonania ({total_time:.2f}s) przekracza 5s"

async def test_api_throughput(
    client: AsyncClient,
    clean_database: AsyncSession
):
    """Test przepustowości API."""
    # Przygotowanie danych
    test_duration = 10  # sekundy
    request_interval = 0.1  # sekundy
    
    async def make_requests():
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < test_duration:
            await client.get("/api/health")
            request_count += 1
            await asyncio.sleep(request_interval)
        
        return request_count
    
    # Uruchomienie wielu klientów
    client_count = 10
    tasks = [make_requests() for _ in range(client_count)]
    request_counts = await asyncio.gather(*tasks)
    
    total_requests = sum(request_counts)
    requests_per_second = total_requests / test_duration
    
    # Asercje
    assert requests_per_second >= 50, f"Przepustowość ({requests_per_second:.2f} req/s) poniżej 50 req/s"

async def test_database_connection_pool(
    client: AsyncClient,
    clean_database: AsyncSession
):
    """Test wydajności puli połączeń do bazy danych."""
    async def make_db_query():
        start_time = time.time()
        await clean_database.execute(text("SELECT 1"))
        return time.time() - start_time
    
    # Wykonanie wielu równoczesnych zapytań
    query_count = 100
    tasks = [make_db_query() for _ in range(query_count)]
    query_times = await asyncio.gather(*tasks)
    
    avg_query_time = statistics.mean(query_times)
    max_query_time = max(query_times)
    
    # Asercje
    assert avg_query_time < 0.01, f"Średni czas zapytania ({avg_query_time:.3f}s) przekracza 10ms"
    assert max_query_time < 0.05, f"Maksymalny czas zapytania ({max_query_time:.3f}s) przekracza 50ms"

async def test_memory_usage(
    client: AsyncClient,
    load_test_users: List[dict],
    clean_database: AsyncSession
):
    """Test zużycia pamięci podczas dużego obciążenia."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Generowanie obciążenia
    tasks = []
    for user_data in load_test_users:
        # Rejestracja
        tasks.append(client.post("/api/users/", json=user_data))
        # Logowanie
        tasks.append(client.post("/api/users/token", data={
            "username": user_data["email"],
            "password": user_data["password"]
        }))
    
    await asyncio.gather(*tasks)
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    # Asercje
    assert memory_increase < 100, f"Wzrost zużycia pamięci ({memory_increase:.1f}MB) przekracza 100MB" 