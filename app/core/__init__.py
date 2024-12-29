"""
Core package zawierający podstawowe komponenty aplikacji.
"""

from .exceptions import (
    BaseAppException,
    ConcurrencyError,
    NetworkException,
    ServiceUnavailableException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    RateLimitExceededError
)

__all__ = [
    'BaseAppException',
    'ConcurrencyError',
    'NetworkException',
    'ServiceUnavailableException',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'ResourceNotFoundError',
    'RateLimitExceededError'
] 