"""HTTPS-only network helper (encryption in transit, size and time limits)."""
import ssl, urllib.request


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def get_text(url, timeout=15, max_bytes=2_000_000, headers=None):
    if not url.lower().startswith("https://"):
        raise ValueError("only https:// URLs are allowed")
    req = urllib.request.Request(url, headers={"User-Agent": "Arise/0.2", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("response too large")
    return data.decode("utf-8", errors="replace")


class RateLimiter:
    """Allow at most `calls` actions per `seconds` for each key."""

    def __init__(self, calls, seconds):
        self.calls, self.seconds, self.hits = calls, seconds, {}

    def allow(self, key="default", now=None):
        import time
        now = time.monotonic() if now is None else now
        q = [t for t in self.hits.get(key, []) if now - t < self.seconds]
        if len(q) >= self.calls:
            self.hits[key] = q
            return False
        q.append(now)
        self.hits[key] = q
        return True
