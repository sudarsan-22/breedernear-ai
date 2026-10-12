from conftest import auth_headers
from fastapi.testclient import TestClient

from app.main import app
from breedernear_core import impact_service
from breedernear_core import listing_service as svc

client = TestClient(app)


def test_post_checks_are_counted_but_never_stored(fakes):
    store, _, vision = fakes
    vision.draft = vision.draft.model_copy(update={"price_inr": 500})
    svc.check_external_listing("buyer-priya", "Lovebirds 500 per pair, full advance only, courier only", [])
    vision.draft = vision.draft.model_copy(update={"species_common": "Parrot", "price_inr": 800})
    svc.check_external_listing("buyer-priya", "pachai kili kunjugal 2 for 800", [])
    s = impact_service.summary("buyer-priya")
    assert (s["posts_checked"], s["posts_flagged"], s["posts_protected"]) == (2, 2, 1)
    assert store.all_listings() == []                                   # the posts themselves are not kept
    assert set(store.fetch("impact", "posts")) == set(impact_service.COUNTERS)


def test_impact_counts_listings_messages_and_breeders(seeded):
    s = impact_service.summary("buyer-priya")
    assert s["listings_screened"] == 40 and s["listings_blocked"] == 2 and s["listings_caution"] == 6
    assert s["verified_breeders"] >= 0 and s["registered_dog_breeders"] >= 1
    assert "sample" in s["note"]


def test_impact_route_needs_login(seeded):
    assert client.get("/api/impact").status_code == 401
    r = client.get("/api/impact", headers=auth_headers(client, "customer"))
    assert r.status_code == 200 and r.json()["listings_screened"] == 40
