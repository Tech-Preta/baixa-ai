from app.ratelimit import RateLimiter


def test_blocks_after_the_limit_and_resets_when_the_window_passes() -> None:
    now = {"t": 100.0}
    limiter = RateLimiter(limit=2, window_seconds=10, clock=lambda: now["t"])

    assert limiter.check("203.0.113.5").allowed
    assert limiter.check("203.0.113.5").allowed
    blocked = limiter.check("203.0.113.5")
    assert not blocked.allowed
    assert blocked.retry_after == 10

    now["t"] = 110.0
    assert limiter.check("203.0.113.5").allowed


def test_keys_are_independent() -> None:
    limiter = RateLimiter(limit=1, window_seconds=60, clock=lambda: 0.0)
    assert limiter.check("203.0.113.5").allowed
    assert limiter.check("203.0.113.9").allowed
    assert not limiter.check("203.0.113.5").allowed
