
from breedernear_core.catalog import breeders, seed_listings


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


def test_without_photos_there_is_no_duplicate_check():
    r = by_id(seed_listings(photo_hash=lambda path: None))
    assert r["LST-0013"]["trust_level"] == "TRUSTED" and r["LST-0013"]["photo_hashes"] == []


def test_screening_is_computed_not_stored_in_seed_file():
    from breedernear_core.data import load_seed
    raw = load_seed("listings.json")["listings"]
    assert all("screening" not in x and "trust_level" not in x for x in raw)


def test_every_visible_sample_listing_has_its_own_photo_file():
    from breedernear_core.catalog import WEB_DIR
    records = seed_listings()
    for r in records:
        if r["status"] == "BLOCKED":
            assert r["photos"] == []
            continue
        assert r["photos"] and (WEB_DIR / r["photos"][0]).is_file(), r["id"]
    shared = [r["id"] for r in records if r["photos"] == ["img/listings/cockatiel-lutino-1.webp"]]
    assert shared == ["LST-0011", "LST-0013"]                     # the deliberate reused-photo demo


def test_reused_photo_demo_is_caution_with_real_images():
    r = by_id(seed_listings())
    assert "duplicate_photo" in {c["name"] for c in r["LST-0013"]["screening"]["checks"]}
    assert r["LST-0013"]["trust_level"] == "CAUTION"
