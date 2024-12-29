from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class ErrorTypes(str, Enum):
    """Enumy dla typów błędów."""
    
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    DATABASE = "database"
    SYSTEM = "system"

class ErrorMessages(str, Enum):
    """Enumy dla komunikatów błędów."""
    
    INVALID_CREDENTIALS = "Nieprawidłowe dane logowania"
    INACTIVE_USER = "Konto jest nieaktywne"
    TOO_MANY_ATTEMPTS = "Zbyt wiele prób logowania. Spróbuj ponownie później"
    USER_NOT_FOUND = "Użytkownik nie został znaleziony"
    INVALID_TOKEN = "Nieprawidłowy token"
    TOKEN_EXPIRED = "Token wygasł"
    PERMISSION_DENIED = "Brak uprawnień do wykonania tej operacji"
    VALIDATION_ERROR = "Błąd walidacji danych"
    RATE_LIMIT_EXCEEDED = "Przekroczono limit zapytań"
    DATABASE_ERROR = "Błąd bazy danych"
    SYSTEM_ERROR = "Błąd systemu"

class ErrorDetail(BaseModel):
    """Model szczegółów błędu."""
    
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    """Model odpowiedzi z błędem."""
    
    type: ErrorTypes
    message: str
    details: Optional[List[ErrorDetail]] = None
    trace_id: Optional[str] = None 