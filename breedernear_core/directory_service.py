"""Local Breeders (Direct Farm): the breeder directory and breeder pages."""

from breedernear_core import deps
from breedernear_core.catalog import breeders
from breedernear_core.listing_service import ListingError
from breedernear_core.match_service import TRUST_ORDER, _card, _distance, _species_keys, _visible
from breedernear_core.services.geo import resolve_district
from breedernear_core.services.registry import sawb_status

SPECIES_NAMES = {
    "budgerigar": "Budgies", "lovebird_peach_faced": "Lovebirds", "lovebird_fischers": "Lovebirds",
    "cockatiel": "Cockatiels", "zebra_finch": "Finches", "society_finch": "Finches", "canary": "Canaries",
    "labrador": "Labradors", "beagle": "Beagles", "shih_tzu": "Shih Tzus", "persian_cat": "Persian cats",
}


def _published_by_breeder(guest_id: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for lst in deps.get_store().all_listings():
        if lst.get("breeder_id") and _visible(lst, guest_id):
            grouped.setdefault(lst["breeder_id"], []).append(lst)
    return grouped


def _registration(breeder: dict, listings: list[dict]) -> str | None:
    """Dog-breeder registration status from the SIMULATED registry; None for bird and cat breeders."""
    if not any(lst["draft"].get("animal_group") == "dog" for lst in listings):
        return None
    return sawb_status(breeder.get("sawb_registration_no"))


def _summary(breeder: dict, listings: list[dict], home: str | None) -> dict:
    km = _distance(home, breeder["district"]) if home else None
    # A breeder is only as trustworthy as their weakest listing.
    worst = max((TRUST_ORDER.get(lst["trust_level"], 1) for lst in listings), default=1)
    species = list(dict.fromkeys(SPECIES_NAMES.get(lst.get("species_key"), lst["draft"]["species_common"])
                                 for lst in listings))
    return {
        "breeder_id": breeder["id"],
        "name": breeder["display_name"],
        "district": breeder["district"],
        "locality": breeder["locality"],
        "years_experience": breeder["years_experience"],
        "species": species,
        "pets_for_sale": len(listings),
        "trust_level": "TRUSTED" if worst == 0 else "CAUTION",
        "caution_listings": sum(lst["trust_level"] != "TRUSTED" for lst in listings),
        "dog_registration": _registration(breeder, listings),
        "distance_km": round(km) if km is not None else None,
        "distance": None if km is None else ("in your district" if km < 5 else f"about {round(km)} km away"),
        "from_price_inr": min((lst.get("price_inr") or 0 for lst in listings), default=None),
        "sample_data": True,
    }


def list_breeders(guest_id: str, district: str | None = None, species: str | None = None) -> dict:
    home = resolve_district(district) if district else None
    if district and home is None:
        raise ListingError(f"I don't know the district '{district}' yet.")
    keys = _species_keys(species) if species and species.lower() not in ("all", "any") else None
    people = breeders()
    rows = []
    for breeder_id, listings in _published_by_breeder(guest_id).items():
        if keys is not None:
            listings = [lst for lst in listings if lst.get("species_key") in keys]
        if breeder_id in people and listings:
            rows.append(_summary(people[breeder_id], listings, home))
    rows.sort(key=lambda r: (r["distance_km"] if r["distance_km"] is not None else 10**6, r["name"]))
    return {"status": "ok", "district": home, "breeders": rows,
            "note": "Sample breeders (fictional). Registration status uses a simulated registry."}


def get_breeder(guest_id: str, breeder_id: str, district: str | None = None) -> dict:
    breeder = breeders().get(breeder_id)
    listings = _published_by_breeder(guest_id).get(breeder_id, [])
    if breeder is None or not listings:
        raise ListingError("That breeder was not found.")
    home = resolve_district(district) if district else None
    km = _distance(home, breeder["district"]) if home else None
    listings.sort(key=lambda lst: (TRUST_ORDER.get(lst["trust_level"], 2), lst.get("price_inr") or 0))
    return {"status": "ok", "breeder": _summary(breeder, listings, home),
            "pets": [_card(lst, guest_id, km) for lst in listings]}
