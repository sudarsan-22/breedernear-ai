from conftest import DEVICE, auth_headers, make_image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_meta_and_health_are_public():
    assert {"key": "tiruppur", "name": "Tiruppur"} in client.get("/api/meta").json()["districts"]
    assert client.get("/api/health").status_code == 200


def test_browsing_needs_login(seeded):
    assert client.get("/api/pets").status_code == 401


def test_pets_and_breeders_endpoints(seeded):
    headers = auth_headers(client, "customer")
    r = client.get("/api/pets", headers=headers, params={"district": "Tiruppur", "species": "all"})
    assert r.status_code == 200 and r.json()["total"] == 38
    r = client.get("/api/breeders", headers=headers, params={"district": "Tiruppur"})
    assert r.json()["breeders"][0]["distance"] == "in your district"
    assert client.get("/api/breeders/BRD-CBE-001", headers=headers).status_code == 200
    assert client.get("/api/breeders/BRD-NOPE", headers=headers).status_code == 404


def test_quiz_endpoint(fakes):
    quiz = {
        "animal_group": "bird",
        "home_type": "flat",
        "has_young_children": True,
        "time_per_day_minutes": 30,
        "budget_inr": 3000,
    }
    r = client.post("/api/recommend", headers=auth_headers(client, "customer"), json=quiz)
    assert r.json()["options"][0]["species_key"] == "budgerigar"


def test_seller_flow_fill_edit_publish_manage(fakes):
    store, uploads, _ = fakes
    headers = auth_headers(client, "seller")
    me = client.get("/api/auth/me", headers=headers).json()["user"]
    photo = uploads.put(me["id"], make_image(1), "image/jpeg", "listing_photo")
    r = client.post(
        "/api/sell/drafts", headers=headers, json={"text": "4 lutino lovebird pairs", "upload_ids": [photo]}
    )
    draft_id = r.json()["draft_id"]
    r = client.patch(
        f"/api/sell/drafts/{draft_id}",
        headers=headers,
        json={"price_inr": 2000, "health_notes": "Healthy, ringed"},
    )
    assert r.json()["draft"]["price_inr"] == 2000 and "health_notes" not in r.json()["missing_fields"]
    assert (
        client.patch(f"/api/sell/drafts/{draft_id}", headers=headers, json={"price_inr": "free"}).status_code
        == 400
    )
    r = client.post(f"/api/sell/drafts/{draft_id}/publish", headers=headers)
    listing_id = r.json()["listing_id"]
    assert r.json()["listing_status"] == "PUBLISHED" and store.listings[listing_id]["device_id"] == DEVICE
    assert (
        client.patch(
            f"/api/seller/listings/{listing_id}", headers=headers, json={"status": "PAUSED"}
        ).status_code
        == 200
    )
    dash = client.get("/api/seller/dashboard", headers=headers).json()
    assert dash["counts"]["paused"] == 1 and dash["farm"]["farm_name"]
    assert client.delete(f"/api/seller/listings/{listing_id}", headers=headers).status_code == 200
    assert client.get("/api/seller/listings", headers=headers).json()["listings"] == []


def test_customers_cannot_use_seller_routes(fakes):
    headers = auth_headers(client, "customer")
    assert client.post("/api/sell/drafts", headers=headers, json={"text": "budgies"}).status_code == 403
    assert client.get("/api/seller/dashboard", headers=headers).status_code == 403


def test_same_device_sandbox_for_seller_listings(fakes):
    """A seller's listing is visible to accounts on the same device only (rule R33)."""
    seller = auth_headers(client, "seller", device=DEVICE)
    draft = client.post("/api/sell/drafts", headers=seller, json={"text": "4 lutino lovebird pairs"}).json()
    listing_id = client.post(f"/api/sell/drafts/{draft['draft_id']}/publish", headers=seller).json()[
        "listing_id"
    ]
    same_device = auth_headers(client, "customer", device=DEVICE)
    other_device = auth_headers(client, "customer", device="aaaaaaaa-1111-4e8b-9c0a-1234567890ab")
    seen = client.get(f"/api/listings/{listing_id}", headers=same_device)
    assert seen.status_code == 200 and seen.json()["listing"]["breeder"] == "Karthik's Demo Aviary"
    assert not seen.json()["listing"]["is_yours"]
    assert client.get(f"/api/listings/{listing_id}", headers=other_device).status_code == 404
    client.post(
        "/api/enquiries", headers=same_device, json={"listing_id": listing_id, "message": "Available?"}
    )
    inbox = client.get("/api/seller/enquiries", headers=seller).json()["enquiries"]
    assert [e["listing_id"] for e in inbox] == [listing_id]
    views = client.get("/api/seller/dashboard", headers=seller).json()["counts"]["views"]
    assert views == 1


def test_check_endpoint_stores_nothing(fakes):
    store = fakes[0]
    post = {"text": "Lovebirds 500 only, full advance, courier only"}
    r = client.post("/api/check", headers=auth_headers(client, "customer"), json=post)
    assert r.status_code == 200 and r.json()["screening"]["trust_level"] == "CAUTION"
    assert store.listings == {}


def test_starter_kit_and_care_plan_endpoints(fakes):
    headers = auth_headers(client, "customer")
    kit = client.get("/api/starter-kit", headers=headers, params={"species": "budgie", "count": 2}).json()
    assert kit["items"] and kit["min_cage_cm"] == [60, 40, 45]
    plan = client.get("/api/care-plan", headers=headers, params={"species": "budgie", "age_months": 4}).json()
    assert plan["care_plan"]["disclaimer"]
