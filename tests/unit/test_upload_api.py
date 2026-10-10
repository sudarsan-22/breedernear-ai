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


def test_listings_and_enquiries_endpoints(seeded):
    r = client.get("/api/listings", headers=HEADERS, params={"species": "budgie", "district": "Tiruppur"})
    assert r.status_code == 200 and r.json()["results"]
    listing_id = r.json()["results"][0]["listing_id"]
    assert client.get(f"/api/listings/{listing_id}", headers=HEADERS).status_code == 200
    assert client.get("/api/listings/LST-0037", headers=HEADERS).status_code == 404
    r = client.post("/api/enquiries", headers=HEADERS, json={"listing_id": listing_id, "message": "Hi"})
    assert r.status_code == 200 and r.json()["enquiry_id"].startswith("ENQ_")
    assert client.get("/api/breeder/enquiries", headers=HEADERS).json() == {"status": "ok", "enquiries": []}


def test_listings_endpoint_errors_are_400(seeded):
    r = client.get("/api/listings", headers=HEADERS, params={"species": "budgie", "district": "Atlantis"})
    assert r.status_code == 400


def test_cart_endpoints(fakes):
    r = client.post("/api/cart/items", headers=HEADERS, json={"product_id": "PRD-FOOD-001", "quantity": 2})
    assert r.status_code == 200 and r.json()["total_inr"] == 498
    assert client.get("/api/cart", headers=HEADERS).json()["items"][0]["quantity"] == 2
    assert client.delete("/api/cart/items/PRD-FOOD-001", headers=HEADERS).json()["items"] == []
    r = client.post("/api/cart/items", headers=HEADERS, json={"product_id": "PRD-NOPE"})
    assert r.status_code == 400


def test_agent_tree_has_all_sub_agents():
    from agents.breedernear.agent import root_agent
    assert {a.name for a in root_agent.sub_agents} == {
        "listing_agent", "trust_agent", "match_agent", "care_agent"}
