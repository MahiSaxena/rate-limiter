import threading
from collections import deque

from .models import Result


class SlidingWindowState:
    """State for ONE (client, resource) pair."""

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self.timestamps = deque()   #times of ACCEPTED requests, oldest first
        self.lock = threading.Lock()

    def try_acquire(self, now: float) -> Result:
        with self.lock:
            cutoff = now - self.window

            #Expire old timestamps from the front
            while self.timestamps and self.timestamps[0] <= cutoff:
                self.timestamps.popleft()

            #Room left? Accept and record
            if len(self.timestamps) < self.limit:
                self.timestamps.append(now)
                return Result(True, self.limit - len(self.timestamps), 0.0)

            #Full: reject, and do NOT record the rejected request
            retry = self.timestamps[0] + self.window - now
            return Result(False, 0, max(0.0, retry))