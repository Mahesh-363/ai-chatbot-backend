"""
Redis-backed sliding window rate limiter for chat messages.
"""
import logging
import time
from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets.
    Checks per-minute, per-hour, and per-day limits.
    """

    WINDOWS = [
        ("minute", 60, settings.RATE_LIMIT_CHAT_MESSAGES_PER_MINUTE),
        ("hour", 3600, settings.RATE_LIMIT_CHAT_MESSAGES_PER_HOUR),
        ("day", 86400, settings.RATE_LIMIT_CHAT_MESSAGES_PER_DAY),
    ]

    def __init__(self, user):
        self.user = user
        try:
            self._cache = caches["rate_limit"]
            self._redis = self._cache.client.get_client()
        except Exception:
            self._redis = None

    def check(self) -> tuple[bool, int]:
        """
        Returns (allowed: bool, retry_after_seconds: int).
        """
        if self._redis is None:
            return True, 0  # Fail open if Redis unavailable

        now = time.time()

        for window_name, window_seconds, limit in self.WINDOWS:
            key = f"ratelimit:chat:{self.user.id}:{window_name}"
            window_start = now - window_seconds

            pipe = self._redis.pipeline()
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            results = pipe.execute()

            current_count = results[1]

            if current_count >= limit:
                # Find oldest entry to calculate retry_after
                oldest = self._redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window_seconds - now) + 1
                else:
                    retry_after = window_seconds
                logger.warning(
                    "Rate limit hit | user=%s window=%s count=%d limit=%d",
                    self.user.id, window_name, current_count, limit,
                )
                return False, max(1, retry_after)

        # All windows OK — record this request
        for window_name, window_seconds, _ in self.WINDOWS:
            key = f"ratelimit:chat:{self.user.id}:{window_name}"
            pipe = self._redis.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window_seconds + 10)
            pipe.execute()

        return True, 0

    def get_usage(self) -> dict:
        """Return current usage for all windows (for informational responses)."""
        if self._redis is None:
            return {}

        now = time.time()
        usage = {}
        for window_name, window_seconds, limit in self.WINDOWS:
            key = f"ratelimit:chat:{self.user.id}:{window_name}"
            self._redis.zremrangebyscore(key, 0, now - window_seconds)
            count = self._redis.zcard(key)
            usage[window_name] = {"used": count, "limit": limit, "remaining": max(0, limit - count)}
        return usage
