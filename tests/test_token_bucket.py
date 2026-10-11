import pytest
from ratelimiter.token_bucket import TokenBucketState


def test_starts_full_and_drains():
    b = TokenBucketState(capacity=3, refill_rate=1.0, now=0.0)
    results = [b.try_acquire(now=0.0) for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert [r.remaining for r in results] == [2, 1, 0, 0]


def test_retry_after_when_empty():
    b = TokenBucketState(capacity=1, refill_rate=2.0, now=0.0)
    b.try_acquire(now=0.0)

    assert b.try_acquire(now=0.0).retry_after == pytest.approx(0.5)


def test_partial_recovery():
    b = TokenBucketState(capacity=1, refill_rate=1.0, now=0.0)
    b.try_acquire(now=0.0)

    r = b.try_acquire(now=0.6)                  # 0.6 tokens: not enough
    assert not r.allowed
    assert r.retry_after == pytest.approx(0.4)

    assert b.try_acquire(now=1.0).allowed       # 1.0 tokens: enough


def test_refill_is_capped_at_capacity():
    b = TokenBucketState(capacity=2, refill_rate=1.0, now=0.0)
    b.try_acquire(now=0.0)

    r = b.try_acquire(now=1000.0)               # long idle
    assert r.allowed and r.remaining == 1       # 2 tokens (cap), minus 1


def test_backward_clock_does_not_remove_tokens():
    b = TokenBucketState(capacity=2, refill_rate=1.0, now=10.0)
    r = b.try_acquire(now=5.0)

    assert r.allowed and r.remaining == 1