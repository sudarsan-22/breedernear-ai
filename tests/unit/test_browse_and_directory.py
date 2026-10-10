import pytest

from breedernear_core import directory_service as directory
from breedernear_core import match_service
from breedernear_core.listing_service import ListingError

GUEST = "guest-priya"


def test_browse_shows_all_visible_pets_trusted_first_then_nearest(seeded):
    r = match_service.browse_pets(GUEST, "Tiruppur")
    levels = [c["trust_level"] for c in r["results"]]
    assert "BLOCKED" not in levels
    assert levels == sorted(levels, key={"TRUSTED": 0, "CAUTION": 1}.get)
    trusted = [c for c in r["results"] if c["trust_level"] == "TRUSTED"]
    distances = [c["distance_km"] for c in trusted]
    assert distances == sorted(distances)
    assert r["total"] == 38                      # 40 samples minus 2 BLOCKED


def test_browse_filters(seeded):
    dogs = match_service.browse_pets(GUEST, "Tiruppur", "dog", None, True)["results"]
    assert dogs and all(c["animal_group"] == "dog" and c["trust_level"] == "TRUSTED" for c in dogs)
    cheap = match_service.browse_pets(GUEST, None, "budgie", 600)["results"]
    assert cheap and all(c["price_inr"] <= 600 for c in cheap)


def test_browse_cards_carry_fair_range_and_breeder_link(seeded):
    card = match_service.browse_pets(GUEST, "Coimbatore", "lovebird")["results"][0]
    assert card["fair_price_range_inr"] and card["breeder_id"]


def test_browse_unknown_district_or_species_is_friendly(seeded):
    with pytest.raises(ListingError):
        match_service.browse_pets(GUEST, "Atlantis")
    with pytest.raises(ListingError):
        match_service.browse_pets(GUEST, None, "giraffe")


def test_directory_sorted_by_distance_with_registration_status(seeded):
    rows = directory.list_breeders(GUEST, "Tiruppur")["breeders"]
    km = [r["distance_km"] for r in rows]
    assert km == sorted(km)
    by_id = {r["breeder_id"]: r for r in rows}
    assert by_id["BRD-CBE-002"]["dog_registration"] == "valid"
    assert by_id["BRD-KRR-001"]["dog_registration"] == "missing"
    assert by_id["BRD-DGL-001"]["dog_registration"] == "unknown"
    assert by_id["BRD-CBE-001"]["dog_registration"] is None        # bird breeder


def test_breeder_trust_is_their_weakest_listing(seeded):
    rows = {r["breeder_id"]: r for r in directory.list_breeders(GUEST)["breeders"]}
    assert rows["BRD-NMK-001"]["trust_level"] == "CAUTION"            # scam listings
    assert rows["BRD-TPR-002"]["trust_level"] == "TRUSTED"


def test_breeder_with_only_blocked_listings_hidden_and_blocked_never_counted(seeded):
    rows = {r["breeder_id"]: r for r in directory.list_breeders(GUEST)["breeders"]}
    assert rows["BRD-TRY-001"]["pets_for_sale"] == 2                   # 2 of 4 are BLOCKED


def test_directory_species_filter(seeded):
    rows = directory.list_breeders(GUEST, "Coimbatore", "dog")["breeders"]
    assert rows and all(any(s in ("Labradors", "Beagles", "Shih Tzus") for s in r["species"]) for r in rows)


def test_breeder_page_lists_their_pets(seeded):
    r = directory.get_breeder(GUEST, "BRD-CBE-001", "Tiruppur")
    assert r["breeder"]["name"] == "Karthik's Aviary" and len(r["pets"]) == 4
    assert all(p["distance"] == "about 43 km away" for p in r["pets"])
    with pytest.raises(ListingError):
        directory.get_breeder(GUEST, "BRD-NOPE")
