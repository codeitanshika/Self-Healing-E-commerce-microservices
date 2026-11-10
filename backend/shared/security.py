"""
security.py
===========
Lightweight protection for the endpoints that mutate system state
(fault injection, manual heal).

- API key: if the API_KEY env var is set, callers must send a matching
  `X-API-Key` header. If it is unset the check is skipped, so local
  demos keep working with zero setup (a warning is logged at startup).
- Rate limit: a small in-memory sliding window per client IP, so a
  public demo deployment cannot be spammed into a permanent outage.
"""
import hmac
import os
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", 20))        # requests...
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # ...per window (s)

_hits: dict[str, deque] = defaultdict(deque)


def get_api_key() -> str:
    """Read at call time so tests / deployments can change the env var."""
    return os.getenv("API_KEY", "")


def require_api_key(x_api_key: str | None = Header(default=None)):
    """FastAPI dependency: reject the request unless the key matches."""
    expected = get_api_key()
    if not expected:
        return  # auth disabled
    if x_api_key is None or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def rate_limit(request: Request):
    """FastAPI dependency: sliding-window limit per client IP."""
    client = request.client.host if request.client else "unknown"
    now = time.time()
    window = _hits[client]
    while window and now - window[0] > RATE_LIMIT_WINDOW:
        window.popleft()
    if len(window) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded, slow down")
    window.append(now)


def reset_rate_limits():
    _hits.clear()
