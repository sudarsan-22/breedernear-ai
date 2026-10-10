from conftest import auth_headers
from fastapi.testclient import TestClient

from app.main import app
from app.ratelimit import SlidingWindow, is_limited
from breedernear_core.config import get_settings

client = TestClient(app)


def test_window_allows_up_to_limit_then_blocks_until_an_hour_passes():
    w = SlidingWindow()
    assert all(w.allow("k", 3, now=t) for t in (0, 1, 2))
    assert not w.allow("k", 3, now=10)
    assert w.allow("k", 3, now=3601)


def test_only_ai_routes_are_limited():
    assert is_limited("POST", "/run_sse") and is_limited("POST", "/api/check")
    assert is_limited("POST", "/api/sell/drafts/DRF_1/publish") and is_limited("GET", "/api/care-plan")
    assert not is_limited("GET", "/api/pets") and not is_limited("PATCH", "/api/sell/drafts/DRF_1")


def test_guest_gets_429_with_friendly_message_after_limit(fakes):
    headers = auth_headers(client, "customer")
    for _ in range(get_settings().rate_limit_per_hour):
        assert client.post("/api/check", headers=headers, json={"text": "budgie pair 600"}).status_code == 200
    r = client.post("/api/check", headers=headers, json={"text": "budgie pair 600"})
    assert r.status_code == 429 and "try again" in r.json()["detail"]
    assert client.get("/api/pets", headers=headers).status_code == 200      # browsing still works
