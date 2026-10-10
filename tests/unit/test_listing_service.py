import pytest
from conftest import make_image

from breedernear_core import listing_service as svc

GUEST = "guest-karthik"
TEXT = "4 lutino lovebird pairs 5 months ₹1800 per pair Saibaba Colony, Coimbatore"


def upload(uploads, seed=1, guest=GUEST):
    return uploads.put(guest, make_image(seed), "image/jpeg", "listing_photo")


def test_extract_saves_draft_with_normalised_district_and_fair_range(fakes):
    store, uploads, vision = fakes
    result = svc.extract_listing(GUEST, TEXT, [upload(uploads)])
    assert result["status"] == "ok"
    assert result["draft"]["district"] == "coimbatore"
    assert result["fair_price_range_inr"] == [1500, 3000]
    assert vision.extract_calls == [(TEXT, 1)]
    assert store.get_draft(result["draft_id"])["guest_id"] == GUEST


def test_extract_needs_text_or_photo(fakes):
    with pytest.raises(svc.ListingError):
        svc.extract_listing(GUEST, "  ", [])


def test_missing_upload_is_a_friendly_error(fakes):
    with pytest.raises(svc.ListingError, match="not found"):
        svc.extract_listing(GUEST, TEXT, ["UPL_doesnotexist"])


def test_guest_cannot_use_another_guests_photo(fakes):
    _, uploads, _ = fakes
    other = upload(uploads, guest="someone-else")
    with pytest.raises(svc.ListingError):
        svc.extract_listing(GUEST, TEXT, [other])


def test_update_draft_changes_field_and_clears_missing(fakes):
    draft_id = svc.extract_listing(GUEST, TEXT, [])["draft_id"]
    result = svc.update_draft(GUEST, draft_id, "health_notes", "Dewormed, eating seeds and greens")
    assert result["draft"]["health_notes"].startswith("Dewormed")
    assert "health_notes" not in result["missing_fields"]


@pytest.mark.parametrize("field,value", [("trust_level", "TRUSTED"), ("price_inr", "-5"), ("count", "zero")])
def test_update_draft_rejects_bad_fields_and_values(fakes, field, value):
    draft_id = svc.extract_listing(GUEST, TEXT, [])["draft_id"]
    with pytest.raises(svc.ListingError):
        svc.update_draft(GUEST, draft_id, field, value)


def test_other_guest_cannot_edit_or_publish_my_draft(fakes):
    draft_id = svc.extract_listing(GUEST, TEXT, [])["draft_id"]
    with pytest.raises(svc.ListingError):
        svc.update_draft("intruder", draft_id, "price_inr", "100")
    with pytest.raises(svc.ListingError):
        svc.publish_listing("intruder", draft_id)


def test_publish_clean_listing_is_trusted_and_sandboxed(fakes):
    store, uploads, _ = fakes
    draft_id = svc.extract_listing(GUEST, TEXT, [upload(uploads)])["draft_id"]
    result = svc.publish_listing(GUEST, draft_id)
    assert result["listing_status"] == "PUBLISHED"
    assert result["screening"]["trust_level"] == "TRUSTED"
    saved = store.get_listing(result["listing_id"])
    assert saved["visibility"] == "owner_only" and saved["owner_user_id"] == GUEST
    assert saved["species_key"] == "lovebird_peach_faced"
    assert store.get_draft(draft_id) is None


def test_publish_protected_species_is_blocked(fakes):
    store, _, vision = fakes
    vision.draft = vision.draft.model_copy(update={"species_common": "Parrot", "variety": None})
    draft_id = svc.extract_listing(GUEST, "pachai kili kunjugal 2 for 800", [])["draft_id"]
    result = svc.publish_listing(GUEST, draft_id)
    assert result["listing_status"] == "BLOCKED"
    assert store.get_listing(result["listing_id"])["status"] == "BLOCKED"


def test_reused_photo_from_another_listing_is_caution(fakes):
    _, uploads, _ = fakes
    first = svc.extract_listing(GUEST, TEXT, [upload(uploads, seed=5)])["draft_id"]
    svc.publish_listing(GUEST, first)
    copier = "guest-copier"
    second = svc.extract_listing(copier, TEXT, [upload(uploads, seed=5, guest=copier)])["draft_id"]
    result = svc.publish_listing(copier, second)
    assert result["screening"]["trust_level"] == "CAUTION"
    assert any(c["name"] == "duplicate_photo" for c in result["screening"]["checks"])


def test_dog_listing_without_registration_is_caution(fakes):
    _, _, vision = fakes
    vision.draft = vision.draft.model_copy(update={
        "species_common": "Labrador Retriever", "variety": None, "animal_group": "dog",
        "unit": "litter", "price_inr": 25000})
    draft_id = svc.extract_listing(GUEST, "Labrador puppies 45 days 25000", [])["draft_id"]
    result = svc.publish_listing(GUEST, draft_id)
    assert result["screening"]["trust_level"] == "CAUTION"


def test_check_external_listing_flags_scam_and_stores_nothing(fakes):
    store, _, vision = fakes
    vision.draft = vision.draft.model_copy(update={"price_inr": 500})
    post = "Lovebirds 500 per pair, full advance only, courier only"
    result = svc.check_external_listing("buyer-priya", post, [])
    assert result["screening"]["trust_level"] == "CAUTION"
    assert result["screening"]["questions_to_ask_seller"]
    assert store.all_listings() == []


def test_my_listings_only_shows_own(fakes):
    draft_id = svc.extract_listing(GUEST, TEXT, [])["draft_id"]
    svc.publish_listing(GUEST, draft_id)
    assert len(svc.my_listings(GUEST)["listings"]) == 1
    assert svc.my_listings("someone-else")["listings"] == []


def test_code_decides_which_registrations_are_missing(fakes):
    _, _, vision = fakes
    suggested = ["parivesh_registration_id", "health_notes"]
    vision.draft = vision.draft.model_copy(update={"missing_fields": suggested})
    lovebird = svc.extract_listing(GUEST, TEXT, [])
    assert lovebird["missing_fields"] == ["health_notes"]          # peach-faced lutino is not CITES
    vision.draft = vision.draft.model_copy(update={"species_common": "Fischer's lovebird", "variety": None,
                                                   "missing_fields": []})
    assert "parivesh_registration_id" in svc.extract_listing(GUEST, "fischers pair", [])["missing_fields"]
    vision.draft = vision.draft.model_copy(update={"species_common": "Labrador", "animal_group": "dog"})
    assert "sawb_registration_no" in svc.extract_listing(GUEST, "lab puppies", [])["missing_fields"]
