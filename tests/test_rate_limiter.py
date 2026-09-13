import unittest
import time
from api.rate_limiter import TokenBucketRateLimiter, rate_limit

class TestTokenBucketRateLimiter(unittest.TestCase):
    def test_capacity_and_consumption(self):
        limiter = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertFalse(limiter.consume())

    def test_refill_logic(self):
        limiter = TokenBucketRateLimiter(capacity=2, refill_rate=10.0)
        self.assertTrue(limiter.consume())
        self.assertTrue(limiter.consume())
        self.assertFalse(limiter.consume())
        time.sleep(0.15)
        self.assertTrue(limiter.consume())

    def test_rate_limit_decorator_429(self):
        limiter = TokenBucketRateLimiter(capacity=1, refill_rate=0.1)
        @rate_limit(limiter)
        def dummy():
            return {"data": "success"}, 200
        res, code = dummy()
        self.assertEqual(code, 200)
        err_res, err_code = dummy()
        self.assertEqual(err_code, 429)

if __name__ == "__main__":
    unittest.main()
