import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, NetworkError, TimeoutException
from fastapi import status
from app.middleware.error_handler import handle_network_error
from app.core.exceptions import NetworkException, ServiceUnavailableException
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

pytestmark = pytest.mark.asyncio

class MockResponse:
    def __init__(self, status_code: int, data: dict = None):
        self.status_code = status_code
        self._data = data or {}
    
    async def json(self):
        return self._data

@pytest.fixture
def mock_network_error():
    return NetworkError("Connection refused")

@pytest.fixture
def mock_timeout_error():
    return TimeoutException("Request timed out")

@pytest.fixture
def mock_http_client():
    """Mock dla klienta HTTP z kontrolowanymi błędami."""
    client = AsyncMock()
    client.is_closed = False
    client.post = AsyncMock()
    client.get = AsyncMock()
    return client

@pytest.fixture
async def mock_db():
    """Mock dla sesji bazy danych."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

async def test_network_error_handling(
    client: AsyncClient,
    mock_network_error: NetworkError,
    mock_http_client: AsyncMock
):
    """Test obsługi błędu połączenia sieciowego."""
    mock_http_client.post.side_effect = mock_network_error
    
    with patch('app.services.auth_service.client', mock_http_client):
        try:
            response = await client.post("/api/users/token", data={
                "username": "test@example.com",
                "password": "test123"
            })
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            error_data = response.json()
            assert "problem z połączeniem" in error_data["detail"].lower()
            assert "retry_after" in error_data
            assert isinstance(error_data["retry_after"], int)
            
        except Exception as e:
            pytest.fail(f"Test nie powiódł się: {str(e)}")
        finally:
            await mock_http_client.aclose()

async def test_timeout_handling(
    client: AsyncClient,
    mock_timeout_error: TimeoutException,
    mock_http_client: AsyncMock
):
    """Test obsługi timeout'u żądania."""
    mock_http_client.post.side_effect = mock_timeout_error
    
    with patch('app.services.auth_service.client', mock_http_client):
        try:
            response = await client.post("/api/users/token", data={
                "username": "test@example.com",
                "password": "test123"
            })
            
            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
            error_data = response.json()
            assert "przekroczono limit czasu" in error_data["detail"].lower()
            assert "retry_after" in error_data
            
            # Sprawdzenie logowania błędu
            with patch('app.middleware.error_handler.logger') as mock_logger:
                await handle_network_error(mock_timeout_error)
                mock_logger.error.assert_called_once()
                
        except Exception as e:
            pytest.fail(f"Test nie powiódł się: {str(e)}")
        finally:
            await mock_http_client.aclose()

async def test_retry_mechanism(
    client: AsyncClient,
    mock_http_client: AsyncMock,
    mock_db: AsyncSession
):
    """Test mechanizmu ponownych prób po błędzie sieciowym."""
    # Symulacja 2 błędów i sukcesu
    mock_responses = [
        NetworkError("Connection refused"),
        NetworkError("Connection refused"),
        MockResponse(200, {"access_token": "test_token", "token_type": "bearer"})
    ]
    
    mock_http_client.post.side_effect = mock_responses
    
    with patch('app.services.auth_service.client', mock_http_client), \
         patch('app.middleware.error_handler.logger') as mock_logger:
        try:
            response = await client.post("/api/users/token", data={
                "username": "test@example.com",
                "password": "test123"
            })
            
            assert response.status_code == status.HTTP_200_OK
            assert mock_http_client.post.call_count == 3
            assert mock_logger.warning.call_count == 2  # 2 nieudane próby
            
            # Sprawdzenie czy odstępy między próbami są odpowiednie
            calls = mock_http_client.post.call_args_list
            assert len(calls) == 3
            
        except Exception as e:
            pytest.fail(f"Test nie powiódł się: {str(e)}")
        finally:
            await mock_http_client.aclose()

async def test_partial_response_handling(
    client: AsyncClient,
    mock_http_client: AsyncMock
):
    """Test obsługi częściowej odpowiedzi."""
    incomplete_data = {"access_token": None, "token_type": "bearer"}
    mock_http_client.post.return_value = MockResponse(200, incomplete_data)
    
    with patch('app.services.auth_service.client', mock_http_client), \
         patch('app.middleware.error_handler.logger') as mock_logger:
        try:
            response = await client.post("/api/users/token", data={
                "username": "test@example.com",
                "password": "test123"
            })
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            error_data = response.json()
            assert "niepełna odpowiedź" in error_data["detail"].lower()
            
            # Sprawdzenie logowania błędu
            mock_logger.error.assert_called_once()
            
        except Exception as e:
            pytest.fail(f"Test nie powiódł się: {str(e)}")
        finally:
            await mock_http_client.aclose()

async def test_network_error_recovery(
    client: AsyncClient,
    mock_http_client: AsyncMock
):
    """Test odzyskiwania po błędzie sieciowym."""
    # Symulacja awarii i przywrócenia połączenia
    mock_responses = [
        NetworkError("Connection refused"),
        MockResponse(200, {"status": "service recovered"})
    ]
    
    mock_http_client.get.side_effect = mock_responses
    
    with patch('app.services.auth_service.client', mock_http_client):
        try:
            # Pierwsza próba - błąd
            response1 = await client.get("/api/health")
            assert response1.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            
            # Symulacja krótkiego oczekiwania
            await asyncio.sleep(0.1)
            
            # Druga próba - sukces
            response2 = await client.get("/api/health")
            assert response2.status_code == status.HTTP_200_OK
            
        except Exception as e:
            pytest.fail(f"Test nie powiódł się: {str(e)}")
        finally:
            await mock_http_client.aclose()

async def test_concurrent_network_errors(
    client: AsyncClient,
    mock_http_client: AsyncMock
):
    """Test równoczesnych błędów sieciowych."""
    # Symulacja wielu równoczesnych błędów
    mock_http_client.post.side_effect = NetworkError("Connection refused")
    
    with patch('app.services.auth_service.client', mock_http_client):
        try:
            tasks = [
                client.post("/api/users/token", data={
                    "username": "test@example.com",
                    "password": "test123"
                })
                for _ in range(5)
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sprawdzenie czy wszystkie żądania zakończyły się odpowiednim błędem
            for response in responses:
                if isinstance(response, Exception):
                    assert isinstance(response, (NetworkException, ServiceUnavailableException))
                else:
                    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            
        except Exception as e:
            pytest.fail(f"Test nie powiódł się: {str(e)}")
        finally:
            await mock_http_client.aclose() 