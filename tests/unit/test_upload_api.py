from conftest import auth_headers, make_image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_seller_uploads_listing_photo(fakes):
    r = client.post(
        "/api/uploads",
        headers=auth_headers(client, "seller"),
        files={"file": ("bird.jpg", make_image(1), "image/jpeg")},
        data={"kind": "listing_photo"},
    )
    assert r.status_code == 200 and r.json()["upload_id"].startswith("UPL_")


def test_customer_can_upload_screenshots_but_not_listing_photos(fakes):
    headers = auth_headers(client, "customer")
    photo = {"file": ("bird.jpg", make_image(1), "image/jpeg")}
    assert (
        client.post(
            "/api/uploads", headers=headers, files=photo, data={"kind": "external_listing"}
        ).status_code
        == 200
    )
    assert (
        client.post("/api/uploads", headers=headers, files=photo, data={"kind": "listing_photo"}).status_code
        == 403
    )


def test_upload_requires_login(fakes):
    assert (
        client.post("/api/uploads", files={"file": ("bird.jpg", make_image(1), "image/jpeg")}).status_code
        == 401
    )


def test_upload_rejects_wrong_type_size_and_kind(fakes):
    headers = auth_headers(client, "seller")
    assert (
        client.post(
            "/api/uploads", headers=headers, files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")}
        ).status_code
        == 415
    )
    big = b"\xff" * (5 * 1024 * 1024 + 10)
    assert (
        client.post(
            "/api/uploads", headers=headers, files={"file": ("big.jpg", big, "image/jpeg")}
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/uploads",
            headers=headers,
            files={"file": ("b.jpg", make_image(1), "image/jpeg")},
            data={"kind": "selfie"},
        ).status_code
        == 400
    )


def test_listings_and_enquiries_endpoints(seeded):
    headers = auth_headers(client, "customer")
    r = client.get("/api/listings", headers=headers, params={"species": "budgie", "district": "Tiruppur"})
    listing_id = r.json()["results"][0]["listing_id"]
    assert client.get(f"/api/listings/{listing_id}", headers=headers).status_code == 200
    assert client.get("/api/listings/LST-0037", headers=headers).status_code == 404
    r = client.post("/api/enquiries", headers=headers, json={"listing_id": listing_id, "message": "Hi"})
    assert r.status_code == 200 and r.json()["enquiry_id"].startswith("ENQ_")
    assert (
        client.get("/api/enquiries/sent", headers=headers).json()["enquiries"][0]["listing_id"] == listing_id
    )
    bad = client.get("/api/listings", headers=headers, params={"species": "budgie", "district": "Atlantis"})
    assert bad.status_code == 400


def test_cart_endpoints_are_for_customers(fakes):
    headers = auth_headers(client, "customer")
    r = client.post("/api/cart/items", headers=headers, json={"product_id": "PRD-FOOD-001", "quantity": 2})
    assert r.status_code == 200 and r.json()["total_inr"] == 498
    assert client.delete("/api/cart/items/PRD-FOOD-001", headers=headers).json()["items"] == []
    assert client.post("/api/cart/items", headers=headers, json={"product_id": "PRD-NOPE"}).status_code == 400
    assert client.get("/api/cart", headers=auth_headers(client, "seller")).status_code == 403


def test_agent_tree_has_all_sub_agents():
    from agents.breedernear.agent import root_agent

    assert {a.name for a in root_agent.sub_agents} == {
        "listing_agent",
        "trust_agent",
        "match_agent",
        "care_agent",
    }
