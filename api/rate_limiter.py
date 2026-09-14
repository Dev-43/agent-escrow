import time

class TokenBucketRateLimiter:
    """Token bucket rate limiter (incomplete)."""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity

    def consume(self, amount: float = 1.0) -> bool:
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

def rate_limit(limiter: TokenBucketRateLimiter):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if not limiter.consume():
                return {"error": "Rate limited"}, 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator
