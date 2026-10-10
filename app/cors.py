"""CORS headers for responses our own middleware sends before the request reaches the app.

The app's CORS (set up by ADK from settings.cors_origins) only covers responses the app produces; a
gatekeeper 401 or a rate-limit 429 would otherwise reach the browser as an opaque network error.
"""

from breedernear_core.config import get_settings


def cors_headers(scope) -> list[tuple[bytes, bytes]]:
    origin = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k.lower() == b"origin"), None)
    if origin and origin in get_settings().cors_origins:
        return [(b"access-control-allow-origin", origin.encode()), (b"vary", b"Origin")]
    return []
