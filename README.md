# In-Memory Rate Limiter

A thread-safe, in-memory rate limiter for an LLM API gateway. It keeps
independent state per (client, resource) pair and supports two strategies.

## Strategies

- **Sliding Window**: at most N requests in any rolling T-second window.
- **Token Bucket**: bucket of N tokens refilled continuously at R tokens/second.
  Allows bursts, then smooths to the refill rate.

## Usage

```python
from ratelimiter.limiter import RateLimiter
from ratelimiter.models import Config, Strategy

limiter = RateLimiter(
    default_config=Config(Strategy.SLIDING_WINDOW, limit=100, window=60),
    resource_configs={
        "big-model": Config(Strategy.TOKEN_BUCKET, limit=10, refill_rate=0.5),
    },
)

result = limiter.allow("client-1", "big-model")
print(result.allowed, result.remaining, result.retry_after)
print(limiter.get_stats("client-1"))
```

## Design

- One state object per (client, resource), each with its own lock, so clients
  never block each other.
- A short-lived dictionary lock protects get-or-create of state.
- Stats counters are protected by their own lock.
- The clock is injectable (default `time.monotonic`) for deterministic tests.
- Rejected requests are never recorded and never consume capacity.

## Run tests

```bash
pip install -r requirements.txt
python -m pytest -v
```