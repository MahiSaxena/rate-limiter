import threading
import time

from .models import Config, Result, Strategy
from .sliding_window import SlidingWindowState
from .token_bucket import TokenBucketState


class RateLimiter:
    def __init__(self, default_config: Config, resource_configs=None, clock=time.monotonic):
        self.default_config = default_config
        self.resource_configs = resource_configs or {}   # {"resource": Config}
        self.clock = clock                               # injectable for tests

        self._states = {}                                # (client, resource) -> state
        self._states_lock = threading.Lock()             # guards the dict only

        self._stats = {}                                 # client -> {"accepted": n, "rejected": n}
        self._stats_lock = threading.Lock()

    def allow(self, client_id: str, resource: str) -> Result:
        now = self.clock()
        state = self._get_state(client_id, resource, now)
        result = state.try_acquire(now)       # per-key lock is taken in here
        self._record(client_id, result.allowed)
        return result

    def _get_state(self, client_id, resource, now):
        key = (client_id, resource)
        with self._states_lock:               # get-or-create must be atomic
            state = self._states.get(key)
            if state is None:
                state = self._create_state(resource, now)
                self._states[key] = state
            return state

    def _create_state(self, resource, now):
        config = self.resource_configs.get(resource, self.default_config)
        if config.strategy == Strategy.SLIDING_WINDOW:
            return SlidingWindowState(config.limit, config.window)
        if config.strategy == Strategy.TOKEN_BUCKET:
            return TokenBucketState(config.limit, config.refill_rate, now)
        raise ValueError(f"Unknown strategy: {config.strategy}")

    def _record(self, client_id, allowed):
        with self._stats_lock:
            s = self._stats.setdefault(client_id, {"accepted": 0, "rejected": 0})
            s["accepted" if allowed else "rejected"] += 1

    def get_stats(self, client_id=None):
        with self._stats_lock:
            if client_id is not None:
                s = self._stats.get(client_id, {"accepted": 0, "rejected": 0})
                return {**s, "total": s["accepted"] + s["rejected"]}
            accepted = sum(s["accepted"] for s in self._stats.values())
            rejected = sum(s["rejected"] for s in self._stats.values())
            return {"accepted": accepted, "rejected": rejected, "total": accepted + rejected}