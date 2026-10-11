"""Visits and purchase (F18): book a visit, the seller confirms or declines, then "I bought this pet".

No delivery and no payment in the app: buyers see the animal and its parents in person and pay there.
Fictional sample breeders have no account to answer, so their visits are confirmed automatically and labelled.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from breedernear_core import analytics_service, companion_service, deps
from breedernear_core.listing_service import ListingError
from breedernear_core.match_service import _visible_listing, as_viewer

VISITS, SALES = "visits", "sales"
SLOTS = {"morning": "Morning (9–12)", "afternoon": "Afternoon (12–4)", "evening": "Evening (4–7)"}
MAX_DAYS_AHEAD = 30
MAX_OPEN_VISITS = 10


def _now() -> datetime:
    return datetime.now(UTC)


def _public(v: dict) -> dict:
    """What either side sees: never the other side's login or contact details."""
    keys = (
        "id",
        "listing_id",
        "species",
        "breeder",
        "date",
        "slot",
        "slot_label",
        "status",
        "note",
        "seller_note",
        "sample_breeder",
        "created_at",
        "purchased",
        "pet_id",
    )
    return {k: v.get(k) for k in keys}


def request_visit(
    buyer_id: str, listing_id: str, day: str, slot: str, note: str = "", today: date | None = None
) -> dict:
    viewer = as_viewer(buyer_id)
    listing = _visible_listing(viewer, listing_id)
    today = today or _now().date()
    try:
        when = date.fromisoformat(day)
    except ValueError as e:
        raise ListingError("Please choose a date.") from e
    if not today < when <= today + timedelta(days=MAX_DAYS_AHEAD):
        raise ListingError(f"Choose a date in the next {MAX_DAYS_AHEAD} days.")
    if slot not in SLOTS:
        raise ListingError("Choose morning, afternoon or evening.")
    store = deps.get_store()
    mine = store.find(VISITS, buyer_id=viewer.user_id)
    if any(
        v["listing_id"] == listing_id and v["status"] in ("requested", "confirmed") and not v.get("purchased")
        for v in mine
    ):
        raise ListingError("You already have a visit booked for this pet.")
    if sum(v["status"] in ("requested", "confirmed") for v in mine) >= MAX_OPEN_VISITS:
        raise ListingError("You have too many open visit requests. Finish or cancel some first.")
    seller_id = listing.get("owner_user_id")
    visit_id = f"VIS_{uuid.uuid4().hex[:10]}"
    visit = {
        "id": visit_id,
        "listing_id": listing_id,
        "buyer_id": viewer.user_id,
        "seller_id": seller_id,
        "species": listing["draft"]["species_common"],
        "breeder": listing.get("breeder_name") or "Local seller",
        "date": when.isoformat(),
        "slot": slot,
        "slot_label": SLOTS[slot],
        "note": (note or "").strip()[:300],
        "status": "requested" if seller_id else "confirmed",
        "sample_breeder": not seller_id,
        "created_at": _now().isoformat(),
        "purchased": False,
    }
    store.put(VISITS, visit_id, visit)
    analytics_service.record(seller_id, listing, "visit")
    return {
        "status": "ok",
        "visit": _public(visit),
        "note": (
            "Sample breeder: confirmed automatically in this demo."
            if not seller_id
            else "Sent to the breeder. You'll see their answer under Account."
        ),
    }


def buyer_visits(buyer_id: str) -> dict:
    visits = deps.get_store().find(VISITS, buyer_id=as_viewer(buyer_id).user_id)
    return {"status": "ok", "visits": [_public(v) for v in sorted(visits, key=lambda v: v["date"])]}


def seller_visits(seller_id: str) -> dict:
    visits = deps.get_store().find(VISITS, seller_id=seller_id)
    return {"status": "ok", "visits": [_public(v) for v in sorted(visits, key=lambda v: v["date"])]}


def answer_visit(seller_id: str, visit_id: str, action: str, note: str = "") -> dict:
    store = deps.get_store()
    visit = store.fetch(VISITS, visit_id)
    if visit is None or visit.get("seller_id") != seller_id:
        raise ListingError("That visit request was not found.")
    if action not in ("confirm", "decline"):
        raise ListingError("Choose confirm or decline.")
    if visit["status"] != "requested":
        raise ListingError("This visit has already been answered.")
    visit["status"] = "confirmed" if action == "confirm" else "declined"
    visit["seller_note"] = (note or "").strip()[:300] or None
    store.put(VISITS, visit_id, visit)
    return {"status": "ok", "visit": _public(visit)}


def purchase(buyer_id: str, visit_id: str, pet_name: str = "") -> dict:
    """'I bought this pet' after a confirmed visit: records the sale and starts the care companion."""
    store = deps.get_store()
    buyer = as_viewer(buyer_id).user_id
    visit = store.fetch(VISITS, visit_id)
    if visit is None or visit["buyer_id"] != buyer:
        raise ListingError("That visit was not found.")
    if visit["status"] != "confirmed":
        raise ListingError("Mark a pet as bought after a confirmed visit.")
    if visit.get("purchased"):
        raise ListingError("You already marked this pet as bought.")
    listing = store.get_listing(visit["listing_id"])
    if listing is None or listing.get("status") not in ("PUBLISHED",):
        raise ListingError("This listing is no longer available.")
    sale_id = f"SAL_{uuid.uuid4().hex[:10]}"
    price = listing.get("price_inr") or 0
    store.put(
        SALES,
        sale_id,
        {
            "id": sale_id,
            "listing_id": listing["id"],
            "buyer_id": buyer,
            "seller_id": listing.get("owner_user_id"),
            "visit_id": visit_id,
            "price_inr": price,
            "units": 1,
            "at": _now().isoformat(),
            "paid_in_person": True,
        },
    )
    if listing.get("owner_user_id"):  # shared sample listings stay unchanged for other judges
        count = (listing["draft"].get("count") or 1) - 1
        listing["draft"]["count"] = max(0, count)
        if count <= 0:
            listing["status"] = "SOLD"
        store.save_listing(listing["id"], listing)
    analytics_service.record(listing.get("owner_user_id"), listing, "sale", price)
    pet = companion_service.start_pet(buyer, listing, sale_id, pet_name)
    visit["purchased"], visit["pet_id"] = True, pet["id"]
    store.put(VISITS, visit_id, visit)
    return {
        "status": "ok",
        "sale_id": sale_id,
        "pet_id": pet["id"],
        "pet_name": pet["name"],
        "note": "Recorded. Payment happens in person, never in this app. Your care companion is ready.",
    }
