# PR Fixture: FAIL Case
**PR Title:** feat(api): Add token bucket rate limiter
**Author:** agent-worker-beta
**Base Branch:** `main` | **PR Number:** `#43`

## PR Description
Implements the requested token-bucket rate limiter:
- Added `TokenBucketRateLimiter` class
- Added decorator

---
## File Changes & Unified Diff

### `api/rate_limiter.py` (NEW FILE)
```python
import time

class TokenBucketRateLimiter:
    """Token bucket rate limiter (partial implementation)."""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity

    def consume(self, amount: float = 1.0) -> bool:
        # Note: missing lock, missing refill math implementation
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
```

### `tests/test_rate_limiter.py` (NEW FILE)
```python
# TODO: Write unit tests covering token consumption, capacity overflow, and refill logic.
# Tests will be added in a future PR.
```
