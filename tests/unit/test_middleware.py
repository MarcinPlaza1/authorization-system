import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.performance import CacheControlMiddleware

@pytest.fixture
def app():
    """Fixture zwracający testową aplikację FastAPI."""
    app = FastAPI()
    app.add_middleware(CacheControlMiddleware)
    
    @app.get("/api/auth/login")
    async def auth_endpoint():
        return {"message": "auth"}
    
    @app.get("/api/users")
    async def api_endpoint():
        return {"message": "api"}
    
    @app.get("/static/file.css")
    async def static_endpoint():
        return {"message": "static"}
    
    return app

@pytest.fixture
def client(app):
    """Fixture zwracający testowego klienta."""
    return TestClient(app)

def test_cache_control_auth_endpoint(client):
    """Test nagłówków cache dla endpointu auth."""
    response = client.get("/api/auth/login")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"

def test_cache_control_api_endpoint(client):
    """Test nagłówków cache dla endpointu API."""
    response = client.get("/api/users")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=300"

def test_cache_control_static_endpoint(client):
    """Test nagłówków cache dla endpointu statycznego."""
    response = client.get("/static/file.css")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=86400" 