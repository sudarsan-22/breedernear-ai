from conftest import make_image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"X-Guest-Id": "3f2b9c1e-7a4d-4e8b-9c0a-1234567890ab"}


def test_upload_photo_returns_id(fakes):
    r = client.post("/api/uploads", headers=HEADERS,
                    files={"file": ("bird.jpg", make_image(1), "image/jpeg")}, data={"kind": "listing_photo"})
    assert r.status_code == 200
    assert r.json()["upload_id"].startswith("UPL_")


def test_upload_requires_guest_id(fakes):
    r = client.post("/api/uploads", files={"file": ("bird.jpg", make_image(1), "image/jpeg")})
    assert r.status_code == 400


def test_upload_rejects_wrong_type(fakes):
    pdf = ("x.pdf", b"%PDF-1.4", "application/pdf")
    r = client.post("/api/uploads", headers=HEADERS, files={"file": pdf})
    assert r.status_code == 415


def test_upload_rejects_too_large(fakes):
    big = b"\xff" * (5 * 1024 * 1024 + 10)
    r = client.post("/api/uploads", headers=HEADERS, files={"file": ("big.jpg", big, "image/jpeg")})
    assert r.status_code == 413


def test_upload_rejects_unknown_kind(fakes):
    r = client.post("/api/uploads", headers=HEADERS,
                    files={"file": ("bird.jpg", make_image(1), "image/jpeg")}, data={"kind": "selfie"})
    assert r.status_code == 400


def test_breeder_listings_endpoint(fakes):
    r = client.get("/api/breeder/listings", headers=HEADERS)
    assert r.status_code == 200 and r.json()["listings"] == []


def test_agent_tree_has_listing_and_trust_agents():
    from agents.breedernear.agent import root_agent
    assert {a.name for a in root_agent.sub_agents} == {"listing_agent", "trust_agent"}
