"""Curated sample listings (data/seed/listings.json), screened by the same code as guest listings.

Screening is never stored by hand in the seed file: it is computed here, so the sample data can't
disagree with the trust rules.
"""

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from breedernear_core.data import load_seed
from breedernear_core.safety.price_rules import price_range
from breedernear_core.safety.species_rules import species_key_for
from breedernear_core.safety.trust_score import ScreeningInputs, screen
from breedernear_core.schemas import ListingDraft
from breedernear_core.services.images import dhash, find_duplicate
from breedernear_core.services.registry import sawb_status

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DRAFT_FIELDS = ("species_common", "variety", "animal_group", "count", "unit", "age_months", "price_inr",
                "locality", "health_notes", "sawb_registration_no", "parivesh_registration_id")


@lru_cache(maxsize=128)
def _photo_hash(path: str) -> str | None:
    file = WEB_DIR / path
    return dhash(file.read_bytes()) if file.is_file() else None


def breeders() -> dict[str, dict]:
    return {b["id"]: b for b in load_seed("breeders.json")["breeders"]}


def _describe(item: dict, breeder: dict) -> str:
    unit = {"pair": "pairs", "litter": "litters"}.get(item["unit"], "available")
    variety = f"{item['variety']} " if item.get("variety") else ""
    return (f"{item['count']} {unit}: {variety}{item['species_common']}, {item['age_months']} months old, "
            f"from {breeder['display_name']} ({breeder['locality']}).")


def seed_listings(photo_hash: Callable[[str], str | None] = _photo_hash) -> list[dict]:
    people = breeders()
    records: list[dict] = []
    known_hashes: dict[str, str] = {}
    for item in load_seed("listings.json")["listings"]:
        breeder = people[item["breeder_id"]]
        draft = ListingDraft(**{k: item.get(k) for k in DRAFT_FIELDS if item.get(k) is not None},
                             district=breeder["district"], description=_describe(item, breeder))
        species_key = species_key_for(draft.species_common, draft.variety or "", item["raw_text"])
        h = photo_hash(item["photo"]) if item.get("photo") else None
        duplicate = find_duplicate(h, known_hashes) if h else None
        screening = screen(ScreeningInputs(
            draft=draft, raw_text=item["raw_text"], duplicate_of=duplicate,
            price_range=price_range(species_key, draft.variety),
            sawb_status=sawb_status(draft.sawb_registration_no) if draft.animal_group == "dog" else None,
        ))
        if h:
            known_hashes[item["id"]] = h
        records.append({
            "id": item["id"],
            "breeder_id": breeder["id"],
            "breeder_name": breeder["display_name"],
            "owner_guest_id": None,
            "visibility": "public",
            "status": "BLOCKED" if screening.trust_level == "BLOCKED" else "PUBLISHED",
            "draft": draft.model_dump(),
            "raw_text": item["raw_text"],
            "photos": [item["photo"]] if item.get("photo") else [],
            "photo_hashes": [h] if h else [],
            "screening": screening.model_dump(),
            "trust_level": screening.trust_level,
            "trust_score": screening.trust_score,
            "species_key": species_key,
            "district": breeder["district"],
            "price_inr": draft.price_inr,
            "created_at": item["created_at"],
            "demo_case": item.get("demo_case"),
            "simulated": True,
        })
    return records
