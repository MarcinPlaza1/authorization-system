"""
FastAPI application package.
"""

from fastapi import FastAPI
from .core import (
    BaseAppException,
    ConcurrencyError,
    NetworkException,
    ServiceUnavailableException
)

__version__ = "0.1.0"

__all__ = [
    'FastAPI',
    'BaseAppException',
    'ConcurrencyError',
    'NetworkException',
    'ServiceUnavailableException'
] 