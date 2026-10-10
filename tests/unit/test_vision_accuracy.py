"""The photo accuracy test set is well formed and scored with the app's own protected rule."""

import json

from breedernear_core.schemas import PhotoScreen
from scripts import vision_accuracy as va


def _photo(**kw) -> PhotoScreen:
    return PhotoScreen(**{"species_guess": "Budgerigar", "species_guess_confidence": 0.9} | kw)


def test_every_listing_photo_has_a_label():
    cases = va.domestic_cases()
    assert len(cases) >= 30
    assert all(c["path"].exists() for c in cases)


def test_hard_case_manifest_is_valid():
    cases = json.loads((va.HARD / "cases.json").read_text())["cases"]
    assert len({c["id"] for c in cases}) == len(cases)
    assert sum(c["group"] == "protected" for c in cases) >= 6
    allowed = {"species_any", "protected", "dye", "stock", "quality"}
    assert all(c["expect"] and set(c["expect"]) <= allowed for c in cases)


def test_score_uses_the_protected_rule():
    expect = {"protected": True}
    assert va.score(expect, _photo(species_guess="Rose-ringed parakeet"))["protected"]   # named
    flagged = _photo(species_guess="parrot", possibly_protected_native_species=True)
    assert va.score(expect, flagged)["protected"]
    low = _photo(species_guess="parrot", possibly_protected_native_species=True, species_guess_confidence=0.3)
    assert not va.score(expect, low)["protected"]


def test_score_domestic_photo():
    expect = va.domestic_cases()[0]["expect"]
    good = va.score(expect, _photo())
    assert all(good.values())
    bad = va.score(expect, _photo(species_guess="Indian ringneck", looks_like_stock_or_watermarked=True))
    assert not bad["species"] and not bad["protected"] and not bad["stock"]
