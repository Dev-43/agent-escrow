import time
import threading
from functools import wraps

class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter."""
    def __init__(self, capacity: int, refill_rate: float):
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("Capacity and refill rate must be positive.")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, amount: float = 1.0) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

def rate_limit(limiter: TokenBucketRateLimiter):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not limiter.consume():
                return {"error": "Too Many Requests", "status_code": 429}, 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator
