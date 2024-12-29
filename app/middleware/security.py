from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Callable, List
import time
import os
import logging
import traceback
from datetime import datetime
import secrets
from app.models.errors import ErrorTypes, ErrorMessages, ErrorResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Konfiguracja loggera
logging.basicConfig(
    level=logging.DEBUG if os.getenv("ENVIRONMENT") == "development" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Konfiguracja handlera plików dla błędów
if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = logging.FileHandler(f'logs/errors_{datetime.now().strftime("%Y%m")}.log')
file_handler.setLevel(logging.ERROR)
logger.addHandler(file_handler)

limiter = Limiter(key_func=get_remote_address)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Lista endpointów wymagających CSRF
CSRF_PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
CSRF_EXEMPT_PATHS = {
    "/api/users/token",
    "/api/users/",
    "/api/users/register",
    "/api/auth/login"
}  # Endpointy wyłączone z ochrony CSRF

class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware do ochrony CSRF."""
    
    def __init__(
        self,
        app,
        token_name: str = "csrf_token",
        cookie_name: str = "csrf",
        header_name: str = "X-CSRF-Token",
        secure: bool = True
    ):
        super().__init__(app)
        self.token_name = token_name
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.secure = secure

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Przetwarza request z ochroną CSRF."""
        if not await self.validate_csrf_token(request):
            return JSONResponse(
                status_code=403,
                content=ErrorResponse(
                    error={
                        "code": 403,
                        "message": "Invalid CSRF token",
                        "type": ErrorTypes.AUTHORIZATION_ERROR
                    }
                ).dict()
            )
        
        response = await call_next(request)
        
        # Dodaj nowy token CSRF do odpowiedzi dla GET requestów HTML
        if request.method == "GET" and "text/html" in response.headers.get("content-type", ""):
            token = self.generate_csrf_token()
            response.set_cookie(
                key=self.cookie_name,
                value=token,
                httponly=True,
                secure=self.secure,
                samesite="strict"
            )
            response.headers[self.header_name] = token
        
        return response
    
    def generate_csrf_token(self) -> str:
        """Generuje token CSRF."""
        return secrets.token_urlsafe(32)
    
    async def validate_csrf_token(self, request: Request) -> bool:
        """Sprawdza token CSRF."""
        if request.method not in CSRF_PROTECTED_METHODS:
            return True
            
        if request.url.path in CSRF_EXEMPT_PATHS:
            return True
        
        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)
        
        if not cookie_token or not header_token:
            return False
            
        return secrets.compare_digest(cookie_token, header_token)

def setup_security_middleware(app: FastAPI) -> None:
    """Konfiguruje middleware bezpieczeństwa dla aplikacji."""
    
    # Dodaj CSRF middleware
    app.add_middleware(
        CSRFMiddleware,
        secure=ENVIRONMENT == "production"
    )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handler dla HTTPException."""
        logger.warning(
            f"HTTPException: {exc.status_code} - {exc.detail}\n"
            f"Path: {request.url.path}\n"
            f"Method: {request.method}"
        )
        
        # Obsługa różnych formatów detail
        if isinstance(exc.detail, dict):
            message = exc.detail.get("message", "Błąd")
            details = exc.detail.get("detail")
        else:
            message = str(exc.detail)
            details = None
            
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error={
                    "code": exc.status_code,
                    "message": message,
                    "type": ErrorTypes.AUTHORIZATION_ERROR if exc.status_code in {401, 403} else "http_error",
                    "details": details
                }
            ).dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handler dla nieobsłużonych wyjątków."""
        error_id = f"ERR_{int(time.time())}"
        
        # Szczegółowe logowanie błędu
        logger.error(
            f"Unhandled exception: {error_id}\n"
            f"Path: {request.url.path}\n"
            f"Method: {request.method}\n"
            f"Error: {str(exc)}\n"
            f"Traceback: {''.join(traceback.format_tb(exc.__traceback__))}"
        )
        
        # Różne odpowiedzi dla różnych środowisk
        if ENVIRONMENT == "development":
            content = ErrorResponse(
                error={
                    "code": 500,
                    "message": str(exc),
                    "type": ErrorTypes.SERVER_ERROR,
                    "error_id": error_id,
                    "details": {"traceback": traceback.format_exc()}
                }
            ).dict()
        else:
            content = ErrorResponse(
                error={
                    "code": 500,
                    "message": ErrorMessages.SERVER_ERROR,
                    "type": ErrorTypes.SERVER_ERROR,
                    "error_id": error_id
                }
            ).dict()
        
        return JSONResponse(
            status_code=500,
            content=content
        )

    # CORS - bardziej liberalne w development
    origins = (
        ["*"] if ENVIRONMENT == "development"
        else [os.getenv("FRONTEND_URL", "http://localhost:3000")]
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
        """Dodaje nagłówki bezpieczeństwa do odpowiedzi."""
        try:
            response = await call_next(request)
            
            # Podstawowe nagłówki bezpieczeństwa
            response.headers.update({
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": (
                    "accelerometer=(), "
                    "camera=(), "
                    "geolocation=(), "
                    "gyroscope=(), "
                    "magnetometer=(), "
                    "microphone=(), "
                    "payment=(), "
                    "usb=()"
                )
            })
            
            if ENVIRONMENT == "production":
                # Bardziej restrykcyjne nagłówki w produkcji
                response.headers.update({
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                    "Content-Security-Policy": (
                        "default-src 'self'; "
                        "script-src 'self' 'nonce-{nonce}'; "
                        "style-src 'self' 'nonce-{nonce}'; "
                        "img-src 'self' data: https:; "
                        "font-src 'self'; "
                        "frame-ancestors 'none'; "
                        "form-action 'self'; "
                        "base-uri 'self'; "
                        "object-src 'none'"
                    ).format(nonce=secrets.token_hex(16))
                })
            else:
                # Bardziej liberalne nagłówki w development
                response.headers["Content-Security-Policy"] = (
                    "default-src * 'unsafe-inline' 'unsafe-eval'; "
                    "img-src * data: blob: 'unsafe-inline'; "
                    "connect-src * 'unsafe-inline';"
                )
            
            return response
        except Exception as e:
            logger.error(f"Error in security headers middleware: {str(e)}")
            raise

def setup_rate_limiting(app: FastAPI) -> None:
    """Konfiguruje rate limiting - mniej restrykcyjny w development."""
    
    # Limity zależne od środowiska
    login_limit = "20/minute" if ENVIRONMENT == "development" else "5/minute"
    general_limit = "10/minute" if ENVIRONMENT == "development" else "3/minute"
    
    # Logowanie
    @limiter.limit(login_limit)
    @app.post("/api/users/token")
    async def rate_limit_login(request: Request):
        pass
    
    # Rejestracja
    @limiter.limit(general_limit)
    @app.post("/api/users")
    async def rate_limit_register(request: Request):
        pass
    
    # Reset hasła
    @limiter.limit(general_limit)
    @app.post("/api/users/reset-password")
    async def rate_limit_password_reset(request: Request):
        pass 