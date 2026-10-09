from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_model_and_version():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert not body["model"].startswith("gemini-2")


def test_web_ui_is_served_with_disclaimer():
    response = client.get("/")
    assert response.status_code == 200
    assert "BreederNear AI" in response.text
    assert "Not veterinary advice" in response.text


def test_adk_agent_is_registered():
    response = client.get("/list-apps")
    assert response.status_code == 200
    assert "breedernear" in response.json()
