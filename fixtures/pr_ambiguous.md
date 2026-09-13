# PR Fixture: AMBIGUOUS Case (Borderline / Low Confidence)
**PR Title:** feat(api): Partial token bucket implementation with basic limiter
**Author:** agent-worker-beta
**Base Branch:** `main` | **PR Number:** `#44`

## PR Description
Initial draft for the rate limiter.
Basic token bucket logic is drafted, but refill timing relies on an approximate timestamp check without concurrency locks.
Minimal test included.

---
## File Changes & Unified Diff

### `api/rate_limiter.py` (NEW FILE)
```python
import time

class TokenBucketRateLimiter:
    """Basic rate limiter draft."""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_check = time.time()

    def consume(self, amount: float = 1.0) -> bool:
        # Approximate refill without concurrency lock
        now = time.time()
        elapsed = now - self.last_check
        if elapsed > 1.0:
            self.tokens = self.capacity
            self.last_check = now
            
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

def rate_limit(limiter: TokenBucketRateLimiter):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            allowed = limiter.consume()
            if not allowed:
                return {"error": "Rate limit exceeded"}, 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

### `tests/test_rate_limiter.py` (NEW FILE)
```python
import unittest
from api.rate_limiter import TokenBucketRateLimiter

class TestRateLimiter(unittest.TestCase):
    def test_basic_consume(self):
        limiter = TokenBucketRateLimiter(5, 1.0)
        self.assertTrue(limiter.consume())
        # Note: refill logic, concurrency overflow, and 429 decorator tests are omitted/unverified
```
