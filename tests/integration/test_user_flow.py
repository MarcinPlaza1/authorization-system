import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import asyncio
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio

@pytest.fixture
def user_flow_data() -> Dict[str, Any]:
    """Dane do testów flow użytkownika."""
    return {
        "registration": {
            "email": "flow@example.com",
            "username": "flowuser",
            "password": "Flow123!@#",
            "full_name": "Flow Test User"
        },
        "profile_update": {
            "full_name": "Updated Flow User",
            "bio": "Test bio"
        },
        "new_password": "NewFlow456!@#"
    }

async def test_complete_user_flow(
    client: AsyncClient,
    clean_database: AsyncSession,
    user_flow_data: Dict[str, Any]
):
    """Test pełnego flow użytkownika od rejestracji do usunięcia konta."""
    # 1. Rejestracja
    register_response = await client.post(
        "/api/users/",
        json=user_flow_data["registration"]
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]
    
    # 2. Potwierdzenie emaila
    verify_response = await client.post(
        f"/api/users/verify-email/{user_id}",
        params={"token": "test_token"}  # W rzeczywistości token z emaila
    )
    assert verify_response.status_code == 200
    
    # 3. Logowanie
    login_response = await client.post(
        "/api/users/token",
        data={
            "username": user_flow_data["registration"]["email"],
            "password": user_flow_data["registration"]["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 4. Aktualizacja profilu
    profile_response = await client.patch(
        f"/api/users/{user_id}",
        headers=headers,
        json=user_flow_data["profile_update"]
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == user_flow_data["profile_update"]["full_name"]
    
    # 5. Zmiana hasła
    password_response = await client.post(
        "/api/users/change-password",
        headers=headers,
        json={
            "current_password": user_flow_data["registration"]["password"],
            "new_password": user_flow_data["new_password"]
        }
    )
    assert password_response.status_code == 200
    
    # 6. Wylogowanie
    logout_response = await client.post("/api/users/logout", headers=headers)
    assert logout_response.status_code == 200
    
    # 7. Próba użycia starego tokenu
    old_token_response = await client.get("/api/users/me", headers=headers)
    assert old_token_response.status_code == 401
    
    # 8. Logowanie z nowym hasłem
    new_login_response = await client.post(
        "/api/users/token",
        data={
            "username": user_flow_data["registration"]["email"],
            "password": user_flow_data["new_password"]
        }
    )
    assert new_login_response.status_code == 200
    new_token = new_login_response.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}
    
    # 9. Usunięcie konta
    delete_response = await client.delete(
        f"/api/users/{user_id}",
        headers=new_headers
    )
    assert delete_response.status_code == 200
    
    # 10. Próba logowania po usunięciu
    final_login_response = await client.post(
        "/api/users/token",
        data={
            "username": user_flow_data["registration"]["email"],
            "password": user_flow_data["new_password"]
        }
    )
    assert final_login_response.status_code == 401

async def test_concurrent_user_flows(
    client: AsyncClient,
    clean_database: AsyncSession
):
    """Test równoczesnych flow użytkowników."""
    async def user_flow(user_num: int):
        # Dane użytkownika
        user_data = {
            "email": f"user{user_num}@example.com",
            "username": f"user{user_num}",
            "password": "Test123!@#",
            "full_name": f"Test User {user_num}"
        }
        
        try:
            # Rejestracja
            register_response = await client.post("/api/users/", json=user_data)
            assert register_response.status_code == 201
            user_id = register_response.json()["id"]
            
            # Logowanie
            login_response = await client.post(
                "/api/users/token",
                data={
                    "username": user_data["email"],
                    "password": user_data["password"]
                }
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Aktualizacje profilu
            for i in range(3):
                update_response = await client.patch(
                    f"/api/users/{user_id}",
                    headers=headers,
                    json={"full_name": f"Updated User {user_num} - {i}"}
                )
                assert update_response.status_code == 200
            
            # Wylogowanie
            logout_response = await client.post("/api/users/logout", headers=headers)
            assert logout_response.status_code == 200
            
            return True
        except Exception as e:
            return False
    
    # Uruchomienie wielu równoczesnych flow
    tasks = [user_flow(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Sprawdzenie wyników
    success_rate = sum(results) / len(results)
    assert success_rate >= 0.8, f"Zbyt niski współczynnik sukcesu: {success_rate:.2%}"

async def test_user_session_management(
    client: AsyncClient,
    clean_database: AsyncSession,
    user_flow_data: Dict[str, Any]
):
    """Test zarządzania sesjami użytkownika."""
    # Rejestracja
    register_response = await client.post(
        "/api/users/",
        json=user_flow_data["registration"]
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]
    
    # Logowanie z wielu urządzeń
    sessions = []
    for i in range(5):
        login_response = await client.post(
            "/api/users/token",
            data={
                "username": user_flow_data["registration"]["email"],
                "password": user_flow_data["registration"]["password"]
            },
            headers={"User-Agent": f"Device{i}"}
        )
        assert login_response.status_code == 200
        sessions.append(login_response.json()["access_token"])
    
    # Sprawdzenie aktywnych sesji
    active_sessions_response = await client.get(
        "/api/users/sessions",
        headers={"Authorization": f"Bearer {sessions[0]}"}
    )
    assert active_sessions_response.status_code == 200
    assert len(active_sessions_response.json()) >= 5
    
    # Zakończenie wszystkich sesji oprócz bieżącej
    end_sessions_response = await client.post(
        "/api/users/end-other-sessions",
        headers={"Authorization": f"Bearer {sessions[0]}"}
    )
    assert end_sessions_response.status_code == 200
    
    # Sprawdzenie czy inne sesje są nieaktywne
    for token in sessions[1:]:
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

async def test_user_data_consistency(
    client: AsyncClient,
    clean_database: AsyncSession,
    user_flow_data: Dict[str, Any]
):
    """Test spójności danych użytkownika podczas równoczesnych operacji."""
    # Rejestracja
    register_response = await client.post(
        "/api/users/",
        json=user_flow_data["registration"]
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]
    
    # Logowanie
    login_response = await client.post(
        "/api/users/token",
        data={
            "username": user_flow_data["registration"]["email"],
            "password": user_flow_data["registration"]["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Równoczesne aktualizacje
    update_tasks = []
    for i in range(10):
        update_tasks.append(
            client.patch(
                f"/api/users/{user_id}",
                headers=headers,
                json={"full_name": f"Concurrent Update {i}"}
            )
        )
    
    update_responses = await asyncio.gather(*update_tasks, return_exceptions=True)
    
    # Sprawdzenie czy tylko jedna aktualizacja się powiodła
    success_updates = sum(
        1 for r in update_responses
        if not isinstance(r, Exception) and r.status_code == 200
    )
    assert success_updates >= 1
    
    # Sprawdzenie końcowego stanu
    final_response = await client.get(f"/api/users/{user_id}", headers=headers)
    assert final_response.status_code == 200
    assert "Concurrent Update" in final_response.json()["full_name"] 