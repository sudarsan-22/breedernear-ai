from conftest import make_image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"X-Guest-Id": "3f2b9c1e-7a4d-4e8b-9c0a-1234567890ab"}


def test_meta_lists_districts():
    r = client.get("/api/meta").json()
    assert {"key": "tiruppur", "name": "Tiruppur"} in r["districts"]


def test_pets_and_breeders_endpoints(seeded):
    r = client.get("/api/pets", headers=HEADERS, params={"district": "Tiruppur", "species": "all"})
    assert r.status_code == 200 and r.json()["total"] == 38
    r = client.get("/api/breeders", headers=HEADERS, params={"district": "Tiruppur"})
    assert r.json()["breeders"][0]["distance"] == "in your district"
    assert client.get("/api/breeders/BRD-CBE-001", headers=HEADERS).status_code == 200
    assert client.get("/api/breeders/BRD-NOPE", headers=HEADERS).status_code == 404
    assert client.get("/api/pets", headers=HEADERS, params={"district": "Atlantis"}).status_code == 400


def test_quiz_endpoint():
    quiz = {"animal_group": "bird", "home_type": "flat", "has_young_children": True,
            "time_per_day_minutes": 30, "budget_inr": 3000}
    r = client.post("/api/recommend", json=quiz)
    assert r.json()["options"][0]["species_key"] == "budgerigar"


def test_sell_form_flow_fill_edit_publish(fakes):
    store, uploads, _ = fakes
    photo = uploads.put(HEADERS["X-Guest-Id"], make_image(1), "image/jpeg", "listing_photo")
    body = {"text": "4 lutino lovebird pairs", "upload_ids": [photo]}
    r = client.post("/api/sell/drafts", headers=HEADERS, json=body)
    assert r.status_code == 200
    draft_id = r.json()["draft_id"]
    r = client.patch(f"/api/sell/drafts/{draft_id}", headers=HEADERS,
                     json={"price_inr": 2000, "health_notes": "Healthy, ringed"})
    assert r.json()["draft"]["price_inr"] == 2000 and "health_notes" not in r.json()["missing_fields"]
    bad = client.patch(f"/api/sell/drafts/{draft_id}", headers=HEADERS, json={"price_inr": "free"})
    assert bad.status_code == 400
    r = client.post(f"/api/sell/drafts/{draft_id}/publish", headers=HEADERS)
    assert r.json()["listing_status"] == "PUBLISHED"
    mine = client.get("/api/breeder/listings", headers=HEADERS).json()["listings"]
    assert mine[0]["listing_id"] == r.json()["listing_id"]


def test_sell_draft_belongs_to_its_guest(fakes):
    r = client.post("/api/sell/drafts", headers=HEADERS, json={"text": "4 lutino lovebird pairs"})
    other = {"X-Guest-Id": "aaaaaaaa-7a4d-4e8b-9c0a-1234567890ab"}
    assert client.post(f"/api/sell/drafts/{r.json()['draft_id']}/publish", headers=other).status_code == 400


def test_check_endpoint_stores_nothing(fakes):
    store = fakes[0]
    post = {"text": "Lovebirds 500 only, full advance, courier only"}
    r = client.post("/api/check", headers=HEADERS, json=post)
    assert r.status_code == 200 and r.json()["screening"]["trust_level"] == "CAUTION"
    assert store.listings == {}


def test_starter_kit_and_care_plan_endpoints(fakes):
    kit = client.get("/api/starter-kit", params={"species": "budgie", "count": 2}).json()
    assert kit["items"] and kit["min_cage_cm"] == [60, 40, 45]
    plan = client.get("/api/care-plan", params={"species": "budgie", "age_months": 4}).json()
    assert plan["care_plan"]["disclaimer"]
