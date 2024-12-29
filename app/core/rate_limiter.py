from datetime import datetime, timedelta
from typing import Dict, Tuple

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> Tuple[bool, int]:
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Usuń stare requesty
        self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]
        
        # Sprawdź limit
        if len(self._requests[key]) >= self.max_requests:
            return False, self.window_seconds
        
        # Dodaj nowy request
        self._requests[key].append(now)
        return True, 0 