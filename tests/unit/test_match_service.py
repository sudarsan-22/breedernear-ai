import pytest

from breedernear_core import listing_service
from breedernear_core import match_service as svc

GUEST = "guest-priya"


def names(result):
    return [o["species_key"] for o in result["options"]]


# recommend_species

def test_family_in_flat_with_small_budget_gets_beginner_birds():
    r = svc.recommend_species("bird", "flat", True, True, 30, True, 3000)
    assert names(r)[0] == "budgerigar"
    assert len(r["options"]) <= 3
    assert "cockatiel" not in names(r)


def test_budget_below_range_excludes_species():
    r = svc.recommend_species("any", "house", False, False, 180, True, 1000)
    assert not {"labrador", "beagle", "shih_tzu", "persian_cat", "canary"} & set(names(r))
    excluded = {e["species"]: e["why_not"] for e in r["excluded"]}
    assert any("₹" in reason for reasons in excluded.values() for reason in reasons)


def test_flat_excludes_large_dogs_and_quiet_home_excludes_loud_species():
    r = svc.recommend_species("dog", "flat", False, False, 180, False, 50000)
    assert names(r) == ["shih_tzu"]


def test_first_time_owner_excludes_species_for_experienced_owners():
    r = svc.recommend_species("dog", "house", False, True, 180, True, 50000)
    assert "beagle" not in names(r)


def test_protected_species_are_never_recommended():
    from breedernear_core.safety.species_rules import find_protected
    r = svc.recommend_species("any", "house", False, False, 600, True, 100000)
    assert not any(find_protected(o["species"]) for o in r["options"])


# search_listings

def test_search_sorts_trusted_first_then_distance_then_price(seeded):
    r = svc.search_listings(GUEST, "budgie", "Tirupur", None)
    levels = [c["trust_level"] for c in r["results"]]
    assert levels == sorted(levels, key={"TRUSTED": 0, "CAUTION": 1}.get)
    assert len(r["results"]) <= 4
    first = r["results"][0]
    assert first["district"] == "tiruppur" and first["price_inr"] == 500
    assert first["distance"] == "in your district"
    assert r["results"][2]["distance"].startswith("about ")


def test_search_never_returns_blocked_listings(seeded):
    r = svc.search_listings(GUEST, "bird", "Trichy", None, radius_km=500)
    assert all(c["trust_level"] != "BLOCKED" for c in r["results"])
    for district in ("Trichy", "Coimbatore", "Chennai"):
        found = svc.search_listings(GUEST, "bird", district, None, radius_km=1000)
        assert not {"LST-0037", "LST-0038"} & {c["listing_id"] for c in found["results"]}


def test_search_respects_max_price(seeded):
    r = svc.search_listings(GUEST, "lovebird", "Erode", 2000)
    assert r["results"] and all(c["price_inr"] <= 2000 for c in r["results"])


def test_lovebird_query_matches_both_lovebird_species(seeded):
    r = svc.search_listings(GUEST, "lovebird", "Erode", None, radius_km=1)
    assert {c["species"] for c in r["results"]} >= {"Lovebird", "Fischer's lovebird"}


def test_caution_listing_shows_its_warnings(seeded):
    r = svc.search_listings(GUEST, "Labrador", "Karur", None, radius_km=1)
    card = r["results"][0]
    assert card["trust_level"] == "CAUTION" and card["warnings"]


def test_protected_species_search_is_not_allowed(seeded):
    r = svc.search_listings(GUEST, "pachai kili", "Coimbatore", None)
    assert r["status"] == "not_allowed" and r["legal_alternatives"]


def test_unknown_species_and_district_are_friendly_errors(seeded):
    with pytest.raises(listing_service.ListingError, match="Available"):
        svc.search_listings(GUEST, "giraffe", "Coimbatore", None)
    with pytest.raises(listing_service.ListingError, match="Try one of"):
        svc.search_listings(GUEST, "budgie", "Atlantis", None)


def test_no_nearby_results_offers_further_away(seeded):
    r = svc.search_listings(GUEST, "Shih Tzu", "Coimbatore", None)
    assert r["results"] == [] and r["further_away"][0]["district"] == "bengaluru"


def _own_listing(store, owner, listing_id="LST_own"):
    store.save_listing(listing_id, {
        "id": listing_id, "owner_guest_id": owner, "visibility": "owner_only", "status": "PUBLISHED",
        "draft": {"species_common": "Budgerigar", "variety": None, "district": "tiruppur"},
        "screening": {"checks": [], "questions_to_ask_seller": []}, "trust_level": "TRUSTED",
        "trust_score": 100, "species_key": "budgerigar", "district": "tiruppur", "price_inr": 450})


def test_guest_listings_are_visible_only_to_their_owner(seeded):
    _own_listing(seeded[0], owner="guest-karthik")
    mine = svc.search_listings("guest-karthik", "budgie", "Tiruppur", None)
    others = svc.search_listings(GUEST, "budgie", "Tiruppur", None)
    assert "LST_own" in {c["listing_id"] for c in mine["results"]}
    assert "LST_own" not in {c["listing_id"] for c in others["results"]}
    assert next(c for c in mine["results"] if c["listing_id"] == "LST_own")["is_yours"]


# get_listing and enquiries

def test_get_listing_shows_checks_and_breeder(seeded):
    r = svc.get_listing(GUEST, "LST-0033")
    assert r["breeder"]["simulated"] and r["questions_to_ask_seller"]


def test_blocked_listing_cannot_be_viewed_or_enquired(seeded):
    with pytest.raises(listing_service.ListingError):
        svc.get_listing(GUEST, "LST-0037")
    with pytest.raises(listing_service.ListingError):
        svc.create_enquiry(GUEST, "LST-0037", "Is it available?")


def test_enquiry_is_stored_as_demo(seeded):
    store = seeded[0]
    r = svc.create_enquiry(GUEST, "LST-0009", "  Are the blue budgies still available?  ")
    saved = store.enquiries[r["enquiry_id"]]
    assert saved["demo"] is True and saved["message"] == "Are the blue budgies still available?"
    assert saved["breeder_id"] == "BRD-TPR-001"


def test_enquiry_message_limits(seeded):
    with pytest.raises(listing_service.ListingError):
        svc.create_enquiry(GUEST, "LST-0009", "   ")
    with pytest.raises(listing_service.ListingError):
        svc.create_enquiry(GUEST, "LST-0009", "x" * 501)


def test_enquiries_per_guest_are_capped(seeded):
    for _ in range(svc.MAX_ENQUIRIES_PER_GUEST):
        svc.create_enquiry(GUEST, "LST-0009", "Hello")
    with pytest.raises(listing_service.ListingError, match="maximum"):
        svc.create_enquiry(GUEST, "LST-0009", "Hello")


def test_breeder_inbox_shows_enquiries_on_own_listings_only(seeded):
    _own_listing(seeded[0], owner="guest-karthik")
    # Guest listings are sandboxed, so in the demo the same browser plays buyer and breeder.
    svc.create_enquiry("guest-karthik", "LST_own", "Interested in your budgies")
    svc.create_enquiry(GUEST, "LST-0009", "Hello")
    with pytest.raises(listing_service.ListingError):
        svc.create_enquiry(GUEST, "LST_own", "Other guests can't see it")
    inbox = svc.my_enquiries("guest-karthik")["enquiries"]
    assert [e["listing_id"] for e in inbox] == ["LST_own"]
    assert svc.my_enquiries(GUEST)["enquiries"] == []
