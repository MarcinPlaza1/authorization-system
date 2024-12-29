import asyncio
import random
from typing import Callable, Any, Optional, List, Type
from datetime import datetime, timedelta
from .exceptions import ServiceUnavailableException

class RetryStrategy:
    """Strategia ponownych prób z wykładniczym opóźnieniem."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions or [Exception]
        
        self._attempt = 0
        self._start_time: Optional[datetime] = None
        self._last_error: Optional[Exception] = None
    
    def _calculate_delay(self) -> float:
        """Oblicza opóźnienie dla kolejnej próby."""
        delay = min(
            self.initial_delay * (self.exponential_base ** self._attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Dodaj losowe wahanie ±25%
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)  # Upewnij się, że opóźnienie nie jest ujemne
    
    def _should_retry(self, error: Exception) -> bool:
        """Sprawdza czy należy ponowić próbę."""
        if self._attempt >= self.max_retries:
            return False
            
        return any(isinstance(error, exc_type) for exc_type in self.retry_exceptions)
    
    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Wykonuje funkcję z mechanizmem ponownych prób."""
        self._attempt = 0
        self._start_time = datetime.utcnow()
        
        while True:
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                self._last_error = e
                
                if not self._should_retry(e):
                    raise ServiceUnavailableException(
                        f"Przekroczono maksymalną liczbę prób ({self.max_retries})"
                    ) from e
                
                self._attempt += 1
                delay = self._calculate_delay()
                
                await asyncio.sleep(delay)
    
    @property
    def attempts(self) -> int:
        """Zwraca liczbę wykonanych prób."""
        return self._attempt
    
    @property
    def last_error(self) -> Optional[Exception]:
        """Zwraca ostatni błąd."""
        return self._last_error
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Zwraca czas, który upłynął od pierwszej próby."""
        if self._start_time:
            return datetime.utcnow() - self._start_time
        return None
    
    def reset(self) -> None:
        """Resetuje strategię do stanu początkowego."""
        self._attempt = 0
        self._start_time = None
        self._last_error = None 