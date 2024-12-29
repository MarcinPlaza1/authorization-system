from pydantic_settings import BaseSettings
from typing import Optional
import os
from urllib.parse import urlparse

class Settings(BaseSettings):
    """Klasa konfiguracji aplikacji."""
    
    # Podstawowa konfiguracja
    PROJECT_NAME: str = "FastAPI App"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Konfiguracja bazy danych
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/fastapi_db"
    )
    SQL_ECHO: bool = False
    
    # Konfiguracja JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Konfiguracja Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    @property
    def REDIS_HOST(self) -> str:
        parsed = urlparse(self.REDIS_URL)
        return parsed.hostname or "redis"
    
    @property
    def REDIS_PORT(self) -> int:
        parsed = urlparse(self.REDIS_URL)
        return parsed.port or 6379
    
    @property
    def REDIS_DB(self) -> int:
        parsed = urlparse(self.REDIS_URL)
        path = parsed.path.lstrip("/")
        return int(path) if path else 0
    
    class Config:
        case_sensitive = True

settings = Settings() 