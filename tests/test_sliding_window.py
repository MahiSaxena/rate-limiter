from ratelimiter.sliding_window import SlidingWindowState


def test_accepts_up_to_limit_then_rejects():
    s = SlidingWindowState(limit=3, window=10)
    results = [s.try_acquire(now=0.0) for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert [r.remaining for r in results] == [2, 1, 0, 0]


def test_retry_after_is_time_until_oldest_expires():
    s = SlidingWindowState(limit=1, window=10)
    s.try_acquire(now=0.0)

    assert s.try_acquire(now=4.0).retry_after == 6.0


def test_requests_expire_after_window():
    s = SlidingWindowState(limit=2, window=10)
    s.try_acquire(now=0.0)
    s.try_acquire(now=0.0)

    assert not s.try_acquire(now=9.9).allowed
    assert s.try_acquire(now=10.0).allowed      # boundary: exactly window old = expired


def test_rejected_requests_are_not_recorded():
    s = SlidingWindowState(limit=1, window=10)
    s.try_acquire(now=0.0)
    for t in (1, 2, 3, 4):
        assert not s.try_acquire(now=float(t)).allowed

    assert s.try_acquire(now=10.0).allowed      # lockout was NOT extended by rejected spam


def test_partial_expiry_frees_one_slot():
    s = SlidingWindowState(limit=2, window=10)
    s.try_acquire(now=0.0)
    s.try_acquire(now=6.0)

    r = s.try_acquire(now=10.0)                 # only the t=0 request expired
    assert r.allowed and r.remaining == 0