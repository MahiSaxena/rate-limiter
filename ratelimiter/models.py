from dataclasses import dataclass
from enum import Enum


class Strategy(Enum):
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass(frozen=True)
class Config:
    strategy: Strategy
    limit: int                # sliding: max requests per window | bucket: capacity
    window: float = 60.0      # sliding window length in seconds
    refill_rate: float = 1.0  # token bucket: tokens added per second


@dataclass(frozen=True)
class Result:
    allowed: bool
    remaining: int
    retry_after: float        # seconds until it's worth retrying (0 if allowed)