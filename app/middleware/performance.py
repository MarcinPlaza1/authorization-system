from fastapi import FastAPI, Request, Response
from typing import Callable
import time
import logging
import psutil
import os
from datetime import datetime
from fastapi.responses import JSONResponse
from app.models.errors import ErrorResponse, ErrorTypes
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Metryki Prometheus
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

class PerformanceMiddleware:
    """Middleware do monitorowania wydajności."""
    
    def __init__(
        self,
        app=None,
        slow_request_threshold: float = 1.0,
        max_memory_percent: float = 90.0,
        max_cpu_percent: float = 80.0
    ):
        self.app = app
        self.slow_request_threshold = slow_request_threshold
        self.max_memory_percent = max_memory_percent
        self.max_cpu_percent = max_cpu_percent

    async def __call__(self, scope, receive, send):
        """Przetwarza request z monitorowaniem wydajności."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        path = scope["path"]
        method = scope["method"]
        
        # Inkrementuj licznik aktywnych requestów
        REQUESTS_IN_PROGRESS.labels(
            method=method,
            endpoint=path
        ).inc()
        
        # Sprawdź zasoby systemowe
        if not await self.check_system_resources():
            REQUESTS_IN_PROGRESS.labels(
                method=method,
                endpoint=path
            ).dec()  # Dekrementuj licznik
            
            response = JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    error={
                        "code": 503,
                        "message": "System jest przeciążony. Spróbuj ponownie później.",
                        "type": ErrorTypes.SERVER_ERROR
                    }
                ).model_dump()
            )
            await response(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Oblicz czas przetwarzania
                process_time = time.time() - start_time
                
                # Aktualizuj metryki
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=path,
                    status=message["status"]
                ).inc()
                
                REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=path
                ).observe(process_time)
                
                # Loguj wolne requesty
                if process_time > self.slow_request_threshold:
                    logger.warning(
                        f"Slow request detected:\n"
                        f"Path: {path}\n"
                        f"Method: {method}\n"
                        f"Time: {process_time:.2f}s"
                    )
                
                # Dodaj nagłówki wydajnościowe
                headers = list(message.get("headers", []))
                headers.append((b"X-Process-Time", str(process_time).encode()))
                message["headers"] = headers
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise
        finally:
            # Dekrementuj licznik aktywnych requestów
            REQUESTS_IN_PROGRESS.labels(
                method=method,
                endpoint=path
            ).dec()

    def get_metrics(self):
        """Zwraca aktualne metryki Prometheus."""
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    async def check_system_resources(self):
        """Sprawdza dostępne zasoby systemowe."""
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        if memory_percent > self.max_memory_percent:
            logger.warning(f"High memory usage: {memory_percent}%")
            return False
            
        if cpu_percent > self.max_cpu_percent:
            logger.warning(f"High CPU usage: {cpu_percent}%")
            return False
            
        return True

class CacheControlMiddleware:
    """Middleware do zarządzania cache'owaniem."""
    
    def __init__(self, app):
        self.app = app
        self.cache_config = {
            # Domyślne ustawienia cache dla różnych typów endpointów
            "static": {"max_age": 86400},  # 24h dla statycznych zasobów
            "api": {"max_age": 300},       # 5m dla API
            "auth": {"no_store": True}     # Bez cache dla auth
        }
    
    async def __call__(self, scope, receive, send):
        """Przetwarza request z odpowiednimi nagłówkami cache."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Określ typ endpointu
                path = scope["path"]
                if path.startswith("/api/auth"):
                    endpoint_type = "auth"
                elif path.startswith("/api"):
                    endpoint_type = "api"
                else:
                    endpoint_type = "static"
                
                # Ustaw nagłówki cache
                cache_settings = self.cache_config.get(endpoint_type, {})
                headers = list(message.get("headers", []))
                
                if cache_settings.get("no_store"):
                    headers.append((b"Cache-Control", b"no-store, no-cache, must-revalidate"))
                else:
                    max_age = cache_settings.get("max_age")
                    if max_age:
                        headers.append((b"Cache-Control", f"public, max-age={max_age}".encode()))
                
                message["headers"] = headers
            
            await send(message)

        await self.app(scope, receive, send_wrapper)

def setup_performance_middleware(app: FastAPI) -> None:
    """Konfiguruje middleware wydajnościowe."""
    
    # Dodaj middleware wydajnościowe
    app.add_middleware(
        PerformanceMiddleware,
        max_memory_percent=90.0,
        max_cpu_percent=80.0
    )
    
    # Dodaj middleware cache
    app.add_middleware(CacheControlMiddleware) 