import threading
from ratelimiter.limiter import RateLimiter
from ratelimiter.models import Config, Strategy


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def make_limiter(clock=None):
    return RateLimiter(
        default_config=Config(Strategy.SLIDING_WINDOW, limit=2, window=10),
        resource_configs={"bucket": Config(Strategy.TOKEN_BUCKET, limit=2, refill_rate=1.0)},
        clock=clock or FakeClock(),
    )


def test_clients_are_isolated():
    lim = make_limiter()
    lim.allow("alice", "api")
    lim.allow("alice", "api")

    assert not lim.allow("alice", "api").allowed
    assert lim.allow("bob", "api").allowed


def test_resources_are_isolated():
    lim = make_limiter()
    lim.allow("alice", "api")
    lim.allow("alice", "api")

    assert not lim.allow("alice", "api").allowed
    assert lim.allow("alice", "bucket").allowed


def test_per_resource_strategy_is_used():
    clock = FakeClock()
    lim = make_limiter(clock)
    lim.allow("alice", "bucket")
    lim.allow("alice", "bucket")

    clock.advance(1.0)                          # token bucket refills 1 token
    assert lim.allow("alice", "bucket").allowed
    assert not lim.allow("alice", "bucket").allowed


def test_recovery_after_window():
    clock = FakeClock()
    lim = make_limiter(clock)
    lim.allow("alice", "api")
    lim.allow("alice", "api")
    assert not lim.allow("alice", "api").allowed

    clock.advance(10)
    assert lim.allow("alice", "api").allowed


def test_stats_per_client_and_global():
    lim = make_limiter()
    for _ in range(3):
        lim.allow("alice", "api")               # 2 accepted, 1 rejected
    lim.allow("bob", "api")                     # 1 accepted

    assert lim.get_stats("alice") == {"accepted": 2, "rejected": 1, "total": 3}
    assert lim.get_stats("bob") == {"accepted": 1, "rejected": 0, "total": 1}
    assert lim.get_stats() == {"accepted": 3, "rejected": 1, "total": 4}
    assert lim.get_stats("nobody") == {"accepted": 0, "rejected": 0, "total": 0}


def _hammer(lim, client, resource, n_threads):
    results = []
    lock = threading.Lock()

    def worker():
        allowed = lim.allow(client, resource).allowed
        with lock:
            results.append(allowed)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for th in threads: th.start()
    for th in threads: th.join()
    return results


def test_concurrent_sliding_window_never_over_admits():
    lim = RateLimiter(Config(Strategy.SLIDING_WINDOW, limit=5, window=60), clock=lambda: 0.0)
    results = _hammer(lim, "carol", "api", 200)

    assert sum(results) == 5
    assert lim.get_stats("carol") == {"accepted": 5, "rejected": 195, "total": 200}


def test_concurrent_token_bucket_never_over_admits():
    lim = RateLimiter(Config(Strategy.TOKEN_BUCKET, limit=5, refill_rate=1.0), clock=lambda: 0.0)
    results = _hammer(lim, "carol", "api", 200)

    assert sum(results) == 5