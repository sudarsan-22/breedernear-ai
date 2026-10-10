"""In-memory sliding-window rate limit for every route that calls Gemini.

Per signed-in session (Authorization header, hashed) and per client IP. In memory is enough while
Cloud Run runs a single instance (max-instances 1); the limit resets if the instance restarts.
"""

import hashlib
import re
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from breedernear_core.config import get_settings

WINDOW_SECONDS = 3600
LIMITED = [
    ("POST", re.compile(r"^/run(_sse)?$")),
    ("POST", re.compile(r"^/api/sell/drafts$")),
    ("POST", re.compile(r"^/api/sell/drafts/[^/]+/publish$")),
    ("POST", re.compile(r"^/api/check$")),
    ("GET", re.compile(r"^/api/care-plan$")),
    ("POST", re.compile(r"^/api/auth/(login|signup|demo)$")),      # slows password guessing
]
MESSAGE = "You've used BreederNear a lot in the last hour. Please wait a few minutes and try again."


class SlidingWindow:
    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self.hits[key]
        while hits and now - hits[0] > WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self.hits.clear()


limiter = SlidingWindow()


def is_limited(method: str, path: str) -> bool:
    return any(method == m and pattern.match(path) for m, pattern in LIMITED)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


async def rate_limit_middleware(request: Request, call_next):
    if is_limited(request.method, request.url.path):
        settings = get_settings()
        auth = request.headers.get("authorization", "")
        guest = hashlib.sha256(auth.encode()).hexdigest() if auth else ""
        allowed = limiter.allow(f"ip:{client_ip(request)}", settings.rate_limit_per_ip_hour)
        if allowed and guest:
            allowed = limiter.allow(f"guest:{guest}", settings.rate_limit_per_hour)
        if not allowed:
            return JSONResponse(status_code=429, content={"detail": MESSAGE})
    return await call_next(request)
