"""Breeder listing flow: extract a draft, edit it, publish it with trust screening.

All functions take the guest ID explicitly so they can be tested without ADK.
"""

import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from breedernear_core import deps
from breedernear_core.safety.price_rules import price_range
from breedernear_core.safety.species_rules import find_cites, species_key_for
from breedernear_core.safety.trust_score import ScreeningInputs, screen
from breedernear_core.schemas import ListingDraft, Screening
from breedernear_core.services.geo import resolve_district
from breedernear_core.services.images import dhash, find_duplicate
from breedernear_core.services.registry import sawb_status

MAX_PHOTOS = 4
EDITABLE_FIELDS = {
    "species_common", "variety", "count", "unit", "sex", "age_months", "price_inr", "district",
    "locality", "health_notes", "sawb_registration_no", "parivesh_registration_id", "description",
}


class ListingError(Exception):
    """A problem the agent should explain to the user in plain language."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_images(guest_id: str, upload_ids: list[str]) -> list[tuple[bytes, str]]:
    images = []
    for upload_id in upload_ids[:MAX_PHOTOS]:
        found = deps.get_uploads().get(guest_id, upload_id)
        if found is None:
            raise ListingError(f"Photo {upload_id} was not found. Please upload it again.")
        images.append(found)
    return images


def _fair_range(d: ListingDraft, raw_text: str) -> tuple[int, int] | None:
    return price_range(species_key_for(d.species_common, d.variety or "", raw_text), d.variety)


def _normalise(d: ListingDraft) -> ListingDraft:
    """Code decides which registrations are required; the model only suggests missing fields."""
    district = resolve_district(d.district)
    missing = [f for f in d.missing_fields if f not in ("sawb_registration_no", "parivesh_registration_id")]
    if d.animal_group == "dog" and not d.sawb_registration_no:
        missing.append("sawb_registration_no")
    is_cites = bool(find_cites(d.species_common, d.species_scientific or "", d.variety or ""))
    if is_cites and not d.parivesh_registration_id:
        missing.append("parivesh_registration_id")
    return d.model_copy(update={"district": district or d.district, "missing_fields": missing})


def _summary(draft_id: str, d: ListingDraft, raw_text: str) -> dict:
    rng = _fair_range(d, raw_text)
    return {
        "status": "ok",
        "draft_id": draft_id,
        "draft": d.model_dump(),
        "fair_price_range_inr": list(rng) if rng else None,
        "price_note": ("Based on sample market data." if rng
                       else "No sample price range for this species yet."),
        "missing_fields": d.missing_fields,
    }


def extract_listing(guest_id: str, text: str, upload_ids: list[str]) -> dict:
    if not text.strip() and not upload_ids:
        raise ListingError("Send at least a short message or a photo of the animals.")
    images = _load_images(guest_id, upload_ids)
    draft = _normalise(deps.get_vision().extract_listing(text, images))
    draft_id = f"DRF_{uuid.uuid4().hex[:10]}"
    deps.get_store().save_draft(draft_id, {
        "draft_id": draft_id, "guest_id": guest_id, "raw_text": text,
        "upload_ids": upload_ids[:MAX_PHOTOS], "draft": draft.model_dump(), "created_at": _now(),
    })
    return _summary(draft_id, draft, text)


def _own_draft(guest_id: str, draft_id: str) -> dict:
    record = deps.get_store().get_draft(draft_id)
    if record is None or record["guest_id"] != guest_id:
        raise ListingError("That draft was not found. Please describe the animals again.")
    return record


def update_draft(guest_id: str, draft_id: str, field: str, value: str) -> dict:
    if field not in EDITABLE_FIELDS:
        allowed = ", ".join(sorted(EDITABLE_FIELDS))
        raise ListingError(f"'{field}' can't be edited. Editable fields: {allowed}.")
    record = _own_draft(guest_id, draft_id)
    data = record["draft"] | {field: value}
    data["missing_fields"] = [f for f in data.get("missing_fields", []) if f != field]
    try:
        draft = _normalise(ListingDraft.model_validate(data))
    except ValidationError as e:
        raise ListingError(f"That value doesn't look right for {field}: {e.errors()[0]['msg']}.") from e
    record["draft"] = draft.model_dump()
    deps.get_store().save_draft(draft_id, record)
    return _summary(draft_id, draft, record["raw_text"])


def _screen(guest_id: str, draft: ListingDraft, raw_text: str, upload_ids: list[str],
            exclude_listing: str | None = None) -> tuple[Screening, list[str]]:
    images = _load_images(guest_id, upload_ids)
    photo = deps.get_vision().screen_photos(images) if images else None
    hashes = [dhash(data) for data, _ in images]
    known = {
        f"{lst['id']}#{i}": h
        for lst in deps.get_store().all_listings() if lst["id"] != exclude_listing
        for i, h in enumerate(lst.get("photo_hashes", []))
    }
    duplicate = None
    for h in hashes:
        duplicate = find_duplicate(h, known)
        if duplicate:
            break
    screening = screen(ScreeningInputs(
        draft=draft, raw_text=raw_text, photo=photo,
        duplicate_of=duplicate.split("#")[0] if duplicate else None,
        price_range=_fair_range(draft, raw_text),
        sawb_status=sawb_status(draft.sawb_registration_no) if draft.animal_group == "dog" else None,
    ))
    return screening, hashes


def publish_listing(guest_id: str, draft_id: str) -> dict:
    record = _own_draft(guest_id, draft_id)
    draft = ListingDraft.model_validate(record["draft"])
    screening, hashes = _screen(guest_id, draft, record["raw_text"], record["upload_ids"])
    listing_id = f"LST_{uuid.uuid4().hex[:10]}"
    status = "BLOCKED" if screening.trust_level == "BLOCKED" else "PUBLISHED"
    deps.get_store().save_listing(listing_id, {
        "id": listing_id,
        "owner_guest_id": guest_id,
        "visibility": "owner_only",       # guest listings are sandboxed (rule R33)
        "status": status,
        "draft": draft.model_dump(),
        "raw_text": record["raw_text"],
        "upload_ids": record["upload_ids"],
        "photo_hashes": hashes,
        "screening": screening.model_dump(),
        "trust_level": screening.trust_level,
        "trust_score": screening.trust_score,
        "species_key": species_key_for(draft.species_common, draft.variety or "", record["raw_text"]),
        "district": draft.district,
        "price_inr": draft.price_inr,
        "created_at": _now(),
    })
    deps.get_store().delete_draft(draft_id)
    return {"status": "ok", "listing_id": listing_id, "listing_status": status,
            "screening": screening.model_dump()}


def check_external_listing(guest_id: str, text: str, upload_ids: list[str]) -> dict:
    """Screen a post seen elsewhere (WhatsApp/Instagram). Nothing is stored as a listing."""
    if not text.strip() and not upload_ids:
        raise ListingError("Paste the post text or upload a screenshot to check it.")
    images = _load_images(guest_id, upload_ids)
    draft = _normalise(deps.get_vision().extract_listing(text, images))
    screening, _ = _screen(guest_id, draft, text, upload_ids)
    return {"status": "ok", "extracted": draft.model_dump(), "screening": screening.model_dump()}


def my_listings(guest_id: str) -> dict:
    mine = [lst for lst in deps.get_store().all_listings() if lst.get("owner_guest_id") == guest_id]
    mine.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"status": "ok", "listings": [
        {"listing_id": x["id"], "species": x["draft"]["species_common"], "variety": x["draft"].get("variety"),
         "price_inr": x.get("price_inr"), "status": x["status"], "trust_level": x["trust_level"],
         "trust_score": x["trust_score"]}
        for x in mine
    ]}
