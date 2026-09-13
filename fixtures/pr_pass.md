# PR Fixture: PASS Case
**PR Title:** feat(api): Add token bucket rate limiter with 429 enforcement
**Author:** agent-worker-beta
**Base Branch:** `main` | **PR Number:** `#42`

## PR Description
Implements the requested token-bucket rate limiter per the task agreement criteria:
1. `TokenBucketRateLimiter` class in `api/rate_limiter.py` supporting configurable capacity and refill rate.
2. `@rate_limit` endpoint decorator that returns HTTP 429 when tokens are exhausted.
3. Full test coverage in `tests/test_rate_limiter.py` testing capacity, consumption, and refill math.
4. Uses Python standard library `time` and `threading` (zero new external dependencies).

---
## File Changes & Unified Diff

### `api/rate_limiter.py` (NEW FILE)
```python
import time
import threading
from functools import wraps

class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter."""
    def __init__(self, capacity: int, refill_rate: float):
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("Capacity and refill rate must be positive.")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)  # tokens per second
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, amount: float = 1.0) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            # Refill tokens up to maximum capacity
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

def rate_limit(limiter: TokenBucketRateLimiter):
    """Decorator returning HTTP 429 if rate limit is exceeded."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not limiter.consume():
                return {"error": "Too Many Requests", "status_code": 429}, 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

### `tests/test_rate_limiter.py` (NEW FILE)
```python
import unittest
import time
from api.rate_limiter import TokenBucketRateLimiter, rate_limit

class TestTokenBucketRateLimiter(unittest.TestCase):
    def test_capacity_and_consumption(self):
        limiter = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertFalse(limiter.consume(), "Should reject after capacity exhausted")

    def test_refill_logic(self):
        limiter = TokenBucketRateLimiter(capacity=2, refill_rate=10.0) # 10 tokens/sec
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertFalse(limiter.consume())
        time.sleep(0.15) # Refills ~1.5 tokens
        self.assertTrue(limiter.consume(), "Should allow consume after refill")

    def test_rate_limit_decorator_429(self):
        limiter = TokenBucketRateLimiter(capacity=1, refill_rate=0.1)
        
        @rate_limit(limiter)
        def dummy_endpoint():
            return {"data": "success"}, 200

        res, code = dummy_endpoint()
        self.assertEqual(code, 200)
        
        # Second call immediately must yield 429
        err_res, err_code = dummy_endpoint()
        self.assertEqual(err_code, 429)
        self.assertEqual(err_res["error"], "Too Many Requests")

if __name__ == "__main__":
    unittest.main()
```
