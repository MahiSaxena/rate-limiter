import threading

from .models import Result


class TokenBucketState:
    """State for ONE (client, resource) pair."""

    def __init__(self, capacity: int, refill_rate: float, now: float):
        self.capacity = capacity
        self.refill_rate = refill_rate      # tokens added per second
        self.tokens = float(capacity)       # start with a full bucket
        self.last_refill = now
        self.lock = threading.Lock()

    def try_acquire(self, now: float) -> Result:
        with self.lock:
            #Refill based on time passed since the last request
            elapsed = max(0.0, now - self.last_refill)
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            #Enough for one request? Take a token
            if self.tokens >= 1:
                self.tokens -= 1
                return Result(True, int(self.tokens), 0.0)

            #Not enough: reject. Don't take anything.
            retry = (1 - self.tokens) / self.refill_rate
            return Result(False, 0, retry)