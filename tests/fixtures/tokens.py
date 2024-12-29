from typing import Dict, List
from datetime import datetime, timedelta

# Przykładowe tokeny JWT do testów
test_tokens: List[Dict] = [
    {
        "email": "admin@example.com",
        "scopes": ["admin"],
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "jti": "valid-token-id-1"
    },
    {
        "email": "user@example.com",
        "scopes": ["user"],
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "jti": "valid-token-id-2"
    },
    {
        "email": "expired@example.com",
        "scopes": ["user"],
        "exp": datetime.utcnow() - timedelta(minutes=30),
        "jti": "expired-token-id"
    }
]

# Tokeny do resetowania hasła
password_reset_tokens: List[Dict] = [
    {
        "token": "valid-reset-token-1",
        "user_id": 1,
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "used": False
    },
    {
        "token": "expired-reset-token",
        "user_id": 2,
        "expires_at": datetime.utcnow() - timedelta(hours=1),
        "used": False
    },
    {
        "token": "used-reset-token",
        "user_id": 3,
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "used": True
    }
]

# Przypadki testowe dla walidacji tokenów
token_validation_test_cases = [
    {
        "token": "valid-token-id-1",
        "should_be_valid": True,
        "description": "Token aktywny"
    },
    {
        "token": "expired-token-id",
        "should_be_valid": False,
        "description": "Token wygasły"
    },
    {
        "token": "revoked-token-id",
        "should_be_valid": False,
        "description": "Token unieważniony"
    }
]

# Przypadki testowe dla resetowania hasła
password_reset_test_cases = [
    {
        "token": "valid-reset-token-1",
        "new_password": "NewPass123!@#",
        "should_succeed": True,
        "description": "Poprawne resetowanie hasła"
    },
    {
        "token": "expired-reset-token",
        "new_password": "NewPass123!@#",
        "should_succeed": False,
        "description": "Token wygasł"
    },
    {
        "token": "used-reset-token",
        "new_password": "NewPass123!@#",
        "should_succeed": False,
        "description": "Token już wykorzystany"
    }
]

# Przypadki testowe dla refresh tokenów
refresh_token_test_cases = [
    {
        "refresh_token": "valid-refresh-token",
        "access_token": "expired-access-token",
        "should_refresh": True,
        "description": "Poprawne odświeżenie tokenu"
    },
    {
        "refresh_token": "expired-refresh-token",
        "access_token": "expired-access-token",
        "should_refresh": False,
        "description": "Wygasły refresh token"
    }
]

# Rate limiting test cases
rate_limit_test_cases = [
    {
        "user_id": 1,
        "endpoint": "/api/auth/login",
        "requests_count": 5,
        "time_window": 60,
        "should_block": False,
        "description": "Normalne użycie API"
    },
    {
        "user_id": 2,
        "endpoint": "/api/auth/login",
        "requests_count": 15,
        "time_window": 60,
        "should_block": True,
        "description": "Przekroczony limit requestów"
    }
]