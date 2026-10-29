from app.cache import AnswerCache
from app.ratelimit import RateLimiter


def test_cache_hits_on_normalized_question(tmp_path):
    cache = AnswerCache(tmp_path / "c.sqlite", ttl_s=60)
    events = [{"event": "answer", "data": {"text": "hi"}}]
    cache.put("What improved on RAG?", events)
    assert cache.get("  what improved   on rag ") == events
    assert cache.get("Something else") is None


def test_cache_expires(tmp_path):
    cache = AnswerCache(tmp_path / "c.sqlite", ttl_s=0)
    cache.put("q", [{"event": "answer", "data": {}}])
    assert cache.get("q") is None


def test_rate_limit_blocks_after_limit_and_recovers():
    limiter = RateLimiter(limit=2, window_s=100)
    assert limiter.check("ip", now=0) == (True, 0)
    assert limiter.check("ip", now=1) == (True, 0)
    allowed, retry = limiter.check("ip", now=2)
    assert not allowed and retry == 99
    assert limiter.check("other-ip", now=2)[0]  # separate budget per IP
    assert limiter.check("ip", now=100)[0]  # first hit has left the window
