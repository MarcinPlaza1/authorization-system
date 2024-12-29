import pytest
import asyncio
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import statistics
from dataclasses import dataclass

pytestmark = pytest.mark.asyncio

@dataclass
class LoadTestScenario:
    name: str
    users: int
    requests_per_user: int
    expected_avg_time: float
    expected_max_time: float
    expected_success_rate: float

@pytest.fixture
def load_scenarios() -> List[LoadTestScenario]:
    """Różne scenariusze testów obciążeniowych."""
    return [
        LoadTestScenario(
            name="light_load",
            users=10,
            requests_per_user=5,
            expected_avg_time=0.5,
            expected_max_time=1.0,
            expected_success_rate=0.99
        ),
        LoadTestScenario(
            name="medium_load",
            users=50,
            requests_per_user=10,
            expected_avg_time=0.8,
            expected_max_time=1.5,
            expected_success_rate=0.95
        ),
        LoadTestScenario(
            name="heavy_load",
            users=100,
            requests_per_user=20,
            expected_avg_time=1.2,
            expected_max_time=2.0,
            expected_success_rate=0.90
        ),
        LoadTestScenario(
            name="spike_load",
            users=200,
            requests_per_user=5,
            expected_avg_time=1.5,
            expected_max_time=2.5,
            expected_success_rate=0.85
        )
    ]

@pytest.fixture
def edge_case_data() -> List[Dict[str, Any]]:
    """Dane do testów przypadków granicznych."""
    return [
        {
            "email": "a" * 254 + "@example.com",  # Maksymalna długość emaila
            "username": "u" * 50,  # Maksymalna długość username
            "password": "P" * 72,  # Maksymalna długość hasła dla bcrypt
            "full_name": "N" * 100  # Maksymalna długość nazwy
        },
        {
            "email": "test@" + "a" * 250 + ".com",  # Długa domena
            "username": "user",
            "password": "Pass123!@#",
            "full_name": ""  # Pusta nazwa
        },
        {
            "email": "test+special.chars@example.com",
            "username": "user-with-special-chars_123",
            "password": "!@#$%^&*()",
            "full_name": "Test User 测试用户"  # Unicode
        }
    ]

@pytest.mark.parametrize("scenario", [
    pytest.lazy_fixture("load_scenarios")
])
async def test_parameterized_load(
    client: AsyncClient,
    clean_database: AsyncSession,
    scenario: LoadTestScenario
):
    """Parametryzowany test obciążenia."""
    async def user_session(user_id: int):
        response_times = []
        success_count = 0
        
        for i in range(scenario.requests_per_user):
            start_time = time.time()
            try:
                response = await client.get(f"/api/users/{user_id}")
                if response.status_code == 200:
                    success_count += 1
                response_times.append(time.time() - start_time)
            except Exception:
                response_times.append(time.time() - start_time)
        
        return {
            "response_times": response_times,
            "success_count": success_count
        }
    
    # Uruchomienie sesji użytkowników
    tasks = [user_session(i) for i in range(scenario.users)]
    results = await asyncio.gather(*tasks)
    
    # Analiza wyników
    all_times = [time for r in results for time in r["response_times"]]
    total_success = sum(r["success_count"] for r in results)
    total_requests = scenario.users * scenario.requests_per_user
    
    avg_time = statistics.mean(all_times)
    max_time = max(all_times)
    success_rate = total_success / total_requests
    
    # Asercje
    assert avg_time <= scenario.expected_avg_time, \
        f"Średni czas ({avg_time:.2f}s) przekracza oczekiwany ({scenario.expected_avg_time}s)"
    assert max_time <= scenario.expected_max_time, \
        f"Maksymalny czas ({max_time:.2f}s) przekracza oczekiwany ({scenario.expected_max_time}s)"
    assert success_rate >= scenario.expected_success_rate, \
        f"Współczynnik sukcesu ({success_rate:.2%}) poniżej oczekiwanego ({scenario.expected_success_rate:.2%})"

@pytest.mark.parametrize("test_data", [
    pytest.lazy_fixture("edge_case_data")
])
async def test_edge_cases(
    client: AsyncClient,
    clean_database: AsyncSession,
    test_data: Dict[str, Any]
):
    """Test przypadków granicznych przy rejestracji."""
    # Rejestracja użytkownika
    response = await client.post("/api/users/", json=test_data)
    
    if response.status_code == 201:
        user_data = response.json()
        # Sprawdzenie czy dane zostały zapisane poprawnie
        assert len(user_data["email"]) <= 255
        assert len(user_data["username"]) <= 50
        assert "password" not in user_data
        
        # Próba logowania
        login_response = await client.post("/api/users/token", data={
            "username": test_data["email"],
            "password": test_data["password"]
        })
        assert login_response.status_code == 200
    else:
        # Sprawdzenie czy błąd jest odpowiednio opisany
        error = response.json()
        assert "detail" in error
        assert isinstance(error["detail"], (str, dict))

async def test_concurrent_edge_cases(
    client: AsyncClient,
    clean_database: AsyncSession,
    edge_case_data: List[Dict[str, Any]]
):
    """Test równoczesnej rejestracji użytkowników z granicznymi danymi."""
    # Tworzenie wielu kopii danych testowych
    test_data = []
    for base_data in edge_case_data:
        for i in range(10):
            data = base_data.copy()
            data["email"] = f"user{i}+" + data["email"]
            data["username"] = f"user{i}" + data["username"][:44]  # Zachowanie limitu 50 znaków
            test_data.append(data)
    
    # Równoczesna rejestracja
    tasks = [
        client.post("/api/users/", json=data)
        for data in test_data
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analiza wyników
    success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 201)
    error_count = len(responses) - success_count
    
    # Sprawdzenie czy część żądań zakończyła się sukcesem
    assert success_count > 0, "Żadna rejestracja nie powiodła się"
    assert error_count > 0, "Wszystkie rejestracje powiodły się (oczekiwano niektórych błędów)"

@pytest.mark.parametrize("db_load", [0, 1000, 10000])
async def test_performance_under_db_load(
    client: AsyncClient,
    clean_database: AsyncSession,
    db_load: int
):
    """Test wydajności przy różnym obciążeniu bazy danych."""
    # Generowanie obciążenia bazy
    if db_load > 0:
        base_user = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123!@#",
            "full_name": "Test User"
        }
        
        for i in range(db_load):
            user_data = base_user.copy()
            user_data["email"] = f"user{i}@example.com"
            user_data["username"] = f"user{i}"
            await client.post("/api/users/", json=user_data)
    
    # Test wydajności wyszukiwania
    start_time = time.time()
    response = await client.get("/api/users", params={"page": 1, "per_page": 10})
    response_time = time.time() - start_time
    
    # Limity czasowe zależne od obciążenia
    time_limits = {
        0: 0.1,
        1000: 0.3,
        10000: 1.0
    }
    
    assert response.status_code == 200
    assert response_time <= time_limits[db_load], \
        f"Czas odpowiedzi ({response_time:.2f}s) przekracza limit dla {db_load} rekordów" 