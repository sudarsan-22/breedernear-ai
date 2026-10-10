"""The web app on Firebase Hosting calls the Cloud Run API cross-origin; nothing else may."""

from conftest import auth_headers
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HOSTING = "https://breedernear-ai-2026.web.app"
PREFLIGHT = {"Access-Control-Request-Method": "POST",
             "Access-Control-Request-Headers": "authorization,content-type,x-device-id"}


def test_preflight_from_firebase_hosting_is_allowed_for_ai_and_api_routes():
    for path in ("/run_sse", "/api/auth/login", "/apps/breedernear/users/U1/sessions"):
        r = client.options(path, headers={"Origin": HOSTING, **PREFLIGHT})
        assert r.status_code == 200, path
        assert r.headers["access-control-allow-origin"] == HOSTING
        assert "x-device-id" in r.headers["access-control-allow-headers"].lower()


def test_other_origins_get_no_cors_headers():
    r = client.options("/run_sse", headers={"Origin": "https://evil.example", **PREFLIGHT})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_real_requests_and_gatekeeper_errors_carry_cors_headers(seeded):
    headers = {"Origin": HOSTING, **auth_headers(client, "customer")}
    assert client.get("/api/pets", headers=headers).headers["access-control-allow-origin"] == HOSTING
    r = client.post("/run_sse", headers={"Origin": HOSTING}, json={})        # no token: gatekeeper 401
    assert r.status_code == 401 and r.headers["access-control-allow-origin"] == HOSTING


def test_other_origins_are_refused_outright():
    r = client.post("/api/auth/login", headers={"Origin": "https://evil.example"},
                    json={"login": "a@example.com", "password": "x"})
    assert r.status_code == 403                    # ADK's origin check, before any login attempt
