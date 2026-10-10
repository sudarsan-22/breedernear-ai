"""The ADK runtime is reachable only through the routes the app uses, behind login."""

import pytest
from conftest import auth_headers
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "path",
    [
        "/list-apps",
        "/docs",
        "/openapi.json",
        "/version",
        "/health",
        "/apps/breedernear/app-info",
        "/agent-identity/finalize",
    ],
)
def test_unused_adk_routes_are_closed(path, fakes):
    assert client.get(path).status_code == 404


def test_live_websocket_is_refused(fakes):
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/run_live?app_name=breedernear"):
        pass


def _me(headers):
    return client.get("/api/auth/me", headers=headers).json()["user"]


def test_sessions_need_login_and_must_be_your_own(fakes):
    headers = auth_headers(client, "customer")
    me = _me(headers)
    assert client.post(f"/apps/breedernear/users/{me['id']}/sessions", json={}).status_code == 401
    other = client.post("/apps/breedernear/users/someone-else/sessions", headers=headers, json={})
    assert other.status_code == 403


def test_session_state_gets_the_real_role(fakes):
    headers = auth_headers(client, "customer")
    me = _me(headers)
    r = client.post(
        f"/apps/breedernear/users/{me['id']}/sessions", headers=headers, json={"state": {"role": "seller"}}
    )
    assert r.status_code == 200
    assert r.json()["state"]["role"] == "customer"  # the browser can't claim a role
    session_id = r.json()["id"]
    assert (
        client.get(f"/apps/breedernear/users/{me['id']}/sessions/{session_id}", headers=headers).status_code
        == 200
    )


def test_run_must_use_your_own_user_id(fakes):
    headers = auth_headers(client, "customer")
    body = {
        "app_name": "breedernear",
        "user_id": "someone-else",
        "session_id": "x",
        "new_message": {"role": "user", "parts": [{"text": "hi"}]},
    }
    assert client.post("/run_sse", headers=headers, json=body).status_code == 403
    assert client.post("/run_sse", json=body).status_code == 401


def test_static_app_still_served():
    assert client.get("/").status_code == 200
