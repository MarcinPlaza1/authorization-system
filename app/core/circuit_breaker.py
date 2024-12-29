from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
import asyncio
from .exceptions import ServiceUnavailableException

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normalny stan działania
    OPEN = "OPEN"      # Stan awarii, wszystkie żądania są odrzucane
    HALF_OPEN = "HALF_OPEN"  # Stan testowy, pozwala na ograniczoną liczbę żądań

class CircuitBreaker:
    """Implementacja wzorca Circuit Breaker do obsługi awarii."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout  # w sekundach
        self.half_open_timeout = half_open_timeout  # w sekundach
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
    
    def _should_allow_request(self) -> bool:
        """Sprawdza czy żądanie powinno być dozwolone."""
        now = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (now - self.last_failure_time) > timedelta(seconds=self.reset_timeout):
                self.state = CircuitState.HALF_OPEN
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            if self.last_success_time and (now - self.last_success_time) > timedelta(seconds=self.half_open_timeout):
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                return True
            return True
            
        return False
    
    def _handle_success(self) -> None:
        """Obsługuje udane żądanie."""
        self.last_success_time = datetime.utcnow()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
    
    def _handle_failure(self) -> None:
        """Obsługuje nieudane żądanie."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Wykonuje funkcję z obsługą Circuit Breaker."""
        if not self._should_allow_request():
            raise ServiceUnavailableException("Circuit Breaker jest otwarty")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._handle_success()
            return result
            
        except Exception as e:
            self._handle_failure()
            raise e
    
    @property
    def is_open(self) -> bool:
        """Sprawdza czy Circuit Breaker jest otwarty."""
        return self.state == CircuitState.OPEN
    
    @property
    def failure_rate(self) -> float:
        """Zwraca współczynnik błędów."""
        return self.failure_count / self.failure_threshold if self.failure_threshold > 0 else 0.0
    
    def reset(self) -> None:
        """Resetuje Circuit Breaker do stanu początkowego."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = None 