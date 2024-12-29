from fastapi import HTTPException
from typing import Optional, Dict, Any

class BaseAppException(Exception):
    """Bazowy wyjątek aplikacji."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class ConcurrencyError(BaseAppException):
    """Wyjątek dla błędów współbieżności."""
    def __init__(self, message: str = "Błąd współbieżności", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)

class NetworkException(BaseAppException):
    """Wyjątek dla błędów sieciowych."""
    def __init__(self, message: str = "Błąd sieci", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=503, details=details)

class ServiceUnavailableException(BaseAppException):
    """Wyjątek dla niedostępności usługi."""
    def __init__(self, message: str = "Usługa niedostępna", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=503, details=details)

class ValidationError(BaseAppException):
    """Wyjątek dla błędów walidacji."""
    def __init__(self, message: str = "Błąd walidacji", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)

class AuthenticationError(BaseAppException):
    """Wyjątek dla błędów uwierzytelniania."""
    def __init__(self, message: str = "Błąd uwierzytelniania", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)

class AuthorizationError(BaseAppException):
    """Wyjątek dla błędów autoryzacji."""
    def __init__(self, message: str = "Brak uprawnień", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)

class ResourceNotFoundError(BaseAppException):
    """Wyjątek dla nieznalezionych zasobów."""
    def __init__(self, message: str = "Zasób nie został znaleziony", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, details=details)

class RateLimitExceededError(BaseAppException):
    """Wyjątek dla przekroczenia limitu żądań."""
    def __init__(self, message: str = "Przekroczono limit żądań", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, details=details) 