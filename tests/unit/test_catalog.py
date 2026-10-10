from conftest import make_image

from breedernear_core.catalog import breeders, seed_listings
from breedernear_core.services.images import dhash


def by_id(records):
    return {r["id"]: r for r in records}


def test_about_forty_listings_all_public_and_simulated():
    records = seed_listings()
    assert 35 <= len(records) <= 50
    assert all(r["visibility"] == "public" and r["simulated"] for r in records)
    assert all(r["breeder_id"] in breeders() for r in records)


def test_demo_cases_get_the_expected_trust_level():
    r = by_id(seed_listings())
    assert r["LST-0001"]["trust_level"] == "TRUSTED"
    assert r["LST-0017"]["trust_level"] == "CAUTION"          # CITES without PARIVESH
    assert r["LST-0033"]["trust_level"] == "CAUTION"          # dog without SAWB
    assert r["LST-0034"]["trust_level"] == "CAUTION"          # SAWB number not in registry
    assert r["LST-0035"]["trust_level"] == "CAUTION"          # scam price and language
    for blocked in ("LST-0037", "LST-0038"):                    # protected species
        assert r[blocked]["trust_level"] == "BLOCKED" and r[blocked]["status"] == "BLOCKED"


def test_only_demo_cases_are_not_trusted():
    for r in seed_listings():
        if not r["demo_case"]:
            assert r["trust_level"] == "TRUSTED", r["id"]


def test_reused_photo_is_flagged_once_images_exist():
    same = dhash(make_image(3))
    r = by_id(seed_listings(photo_hash=lambda path: same))
    assert r["LST-0011"]["trust_level"] == "TRUSTED"
    checks = {c["name"] for c in r["LST-0013"]["screening"]["checks"]}
    assert "duplicate_photo" in checks and r["LST-0013"]["trust_level"] == "CAUTION"


def test_screening_is_computed_not_stored_in_seed_file():
    from breedernear_core.data import load_seed
    raw = load_seed("listings.json")["listings"]
    assert all("screening" not in x and "trust_level" not in x for x in raw)
