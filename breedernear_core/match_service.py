"""Buyer flow: which pet suits this home, which trusted listings are nearby, and enquiries.

Filtering, ranking and visibility are decided here in code; the agent only explains the results.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from breedernear_core import deps
from breedernear_core.catalog import WEB_DIR, breeders
from breedernear_core.data import contains_phrase, load_seed, normalize
from breedernear_core.listing_service import ListingError
from breedernear_core.safety.price_rules import price_range
from breedernear_core.safety.species_rules import find_protected
from breedernear_core.services.geo import distance_km, resolve_district

MAX_RESULTS = 4
MAX_OPTIONS = 3
MAX_ENQUIRY_CHARS = 500
MAX_REPLY_CHARS = 800
MAX_ENQUIRIES_PER_GUEST = 30
LEGAL_ALTERNATIVES = ["Budgerigar (budgie)", "Cockatiel", "Peach-faced lovebird", "Zebra finch", "Canary"]
SAMPLE_NOTE = (
    "Sample listings from simulated breeders; prices are sample market data; distances are approximate "
    "(between district centres).")
SPACE_RANK = {"small": 0, "medium": 1, "large": 2}
GROUP_WORDS = {
    "bird": {"bird", "birds", "paravai"},
    "dog": {"dog", "dogs", "puppy", "puppies", "naai", "nai"},
    "cat": {"cat", "cats", "kitten", "kittens", "poonai"},
}
TRUST_ORDER = {"TRUSTED": 0, "CAUTION": 1}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _species() -> list[dict]:
    return load_seed("species.json")["species"]


def _unit(key: str) -> str:
    for entry in load_seed("price_ranges.json")["ranges"]:
        if entry["species_key"] == key:
            return entry["unit"]
    return "single"


def recommend_species(animal_group: str = "any", home_type: str = "flat", has_young_children: bool = False,
                      first_time_owner: bool = True, time_per_day_minutes: int = 60, noise_ok: bool = True,
                      budget_inr: int | None = None) -> dict:
    """Rule-based shortlist. Each exclusion carries its reason so the agent can explain it."""
    group = animal_group.lower().strip()
    is_flat = any(word in home_type.lower() for word in ("flat", "apartment"))
    max_space = "medium" if is_flat else "large"
    options, excluded = [], []
    for sp in _species():
        rng = price_range(sp["key"])
        reasons_out = []
        if group in GROUP_WORDS and sp["group"] != group:
            continue
        if budget_inr is not None and rng and rng[0] > budget_inr:
            per = "pair" if _unit(sp["key"]) == "pair" else "animal"
            reasons_out.append(f"usually costs ₹{rng[0]:,} or more per {per}")
        if SPACE_RANK[sp["space_needed"]] > SPACE_RANK[max_space]:
            reasons_out.append("needs more space than a flat")
        if not noise_ok and sp["noise"] == "high":
            reasons_out.append("can be noisy")
        if first_time_owner and not sp["beginner_friendly"]:
            reasons_out.append("better for experienced owners")
        if time_per_day_minutes < sp["daily_minutes"] * 0.75:
            reasons_out.append(f"needs about {sp['daily_minutes']} minutes of care a day")
        if reasons_out:
            excluded.append({"species": sp["name"], "why_not": reasons_out})
            continue

        why = [f"suits a {'flat' if is_flat else 'house'}",
               f"needs about {sp['daily_minutes']} minutes a day",
               f"noise level: {sp['noise']}"]
        if sp["beginner_friendly"]:
            why.append("good for first-time owners")
        if has_young_children and sp["kid_friendly"]:
            why.append("gentle enough for a family with children")
        watch_outs = list(sp["watch_outs"])
        if has_young_children and not sp["kid_friendly"]:
            watch_outs.insert(0, "Better for older children; supervise young kids.")
        score = (2 * sp["beginner_friendly"] + 2 * (has_young_children and sp["kid_friendly"])
                 - 3 * (has_young_children and not sp["kid_friendly"])
                 + (has_young_children and sp["hands_on"])
                 + {"low": 1, "medium": 0, "high": -1}[sp["noise"]]
                 + (1 if budget_inr and rng and rng[1] <= budget_inr else 0))
        options.append((score, rng[0] if rng else 0, {
            "species": sp["name"], "species_key": sp["key"], "why": why, "watch_outs": watch_outs,
            "typical_price_range_inr": list(rng) if rng else None, "price_unit": _unit(sp["key"]),
            "lifespan_years": sp["lifespan_years"],
        }))
    options.sort(key=lambda o: (-o[0], o[1]))
    return {
        "status": "ok",
        "options": [o[2] for o in options[:MAX_OPTIONS]],
        "excluded": excluded[:4],
        "note": "Based on sample care guidance and sample market prices.",
    }


def _species_keys(query: str) -> set[str]:
    norm = normalize(query)
    words = set(norm.split())
    keys = set()
    for sp in _species():
        names = sp["aliases"] + [sp["name"], sp["key"].replace("_", " ")]
        if words & GROUP_WORDS.get(sp["group"], set()):
            keys.add(sp["key"])
        elif any(contains_phrase(norm, n) or contains_phrase(normalize(n), query) for n in names):
            keys.add(sp["key"])
    return keys


@dataclass(frozen=True)
class Viewer:
    """Who is looking: the signed-in user and the device they use (same-device sandbox, rule R33)."""

    user_id: str
    device_id: str | None = None


def as_viewer(viewer: "Viewer | str") -> Viewer:
    return viewer if isinstance(viewer, Viewer) else Viewer(str(viewer))


def _visible(listing: dict, guest_id: "Viewer | str") -> bool:
    if listing.get("status") != "PUBLISHED":
        return False
    viewer = as_viewer(guest_id)
    if listing.get("visibility") == "public" or listing.get("owner_user_id") == viewer.user_id:
        return True
    return bool(viewer.device_id) and listing.get("device_id") == viewer.device_id


def _price_position(listing: dict) -> str:
    rng = price_range(listing.get("species_key"), listing["draft"].get("variety"))
    price = listing.get("price_inr")
    if not rng or not price:
        return "no sample range"
    if price < 0.5 * rng[0]:
        return "far below the usual range"
    if price < rng[0]:
        return "below the usual range"
    if price > 1.5 * rng[1]:
        return "well above the usual range"
    return "within the usual range"


def _distance_label(km: float | None) -> str | None:
    if km is None:
        return None
    return "in your district" if km < 5 else f"about {round(km)} km away"


def _photo(listing: dict) -> str | None:
    """Path of the first sample photo that exists in web/ (guest photos are never served back)."""
    for path in listing.get("photos") or []:
        if (WEB_DIR / path).is_file():
            return path
    return None


def _card(listing: dict, guest_id: str, km: float | None) -> dict:
    d = listing["draft"]
    rng = price_range(listing.get("species_key"), d.get("variety"))
    warnings = [c["detail"] for c in listing["screening"]["checks"] if c["result"] in ("warn", "block")]
    return {
        "listing_id": listing["id"],
        "species": d["species_common"],
        "variety": d.get("variety"),
        "count": d.get("count"),
        "unit": d.get("unit"),
        "age_months": d.get("age_months"),
        "price_inr": listing.get("price_inr"),
        "price_position": _price_position(listing),
        "district": listing.get("district"),
        "locality": d.get("locality"),
        "distance_km": round(km) if km is not None else None,
        "distance": _distance_label(km),
        "breeder": listing.get("breeder_name") or "Local seller",
        "breeder_id": listing.get("breeder_id"),
        "species_key": listing.get("species_key"),
        "animal_group": d.get("animal_group"),
        "fair_price_range_inr": list(rng) if rng else None,
        "photo": _photo(listing),
        "trust_level": listing["trust_level"],
        "trust_score": listing["trust_score"],
        "warnings": warnings,
        "is_yours": listing.get("owner_user_id") == as_viewer(guest_id).user_id,
        "sample_data": bool(listing.get("simulated")),
    }


def _distance(a: str, b: str | None) -> float | None:
    try:
        return distance_km(a, b) if b else None
    except KeyError:
        return None


def search_listings(guest_id: str, species: str, district: str, max_price_inr: int | None = None,
                    radius_km: int = 60) -> dict:
    protected = find_protected(species)
    if protected:
        return {"status": "not_allowed",
                "message": f"{protected[0].common_name} is a protected Indian native species; "
                           "buying or selling it is illegal under the Wild Life (Protection) Act, 1972.",
                "legal_alternatives": LEGAL_ALTERNATIVES}
    keys = _species_keys(species)
    if not keys:
        names = ", ".join(sp["name"] for sp in _species())
        raise ListingError(f"I don't have listings for '{species}' yet. Available: {names}.")
    home = resolve_district(district)
    if home is None:
        names = ", ".join(d["name"] for d in load_seed("districts.json")["districts"])
        raise ListingError(f"I don't know the district '{district}' yet. Try one of: {names}.")

    matches = []
    for lst in deps.get_store().all_listings():
        if not _visible(lst, guest_id) or lst.get("species_key") not in keys:
            continue
        if max_price_inr is not None and (lst.get("price_inr") or 0) > max_price_inr:
            continue
        km = _distance(home, lst.get("district"))
        if km is None:
            continue
        matches.append((TRUST_ORDER.get(lst["trust_level"], 2), km, lst.get("price_inr") or 0, lst))
    matches.sort(key=lambda m: m[:3])
    nearby = [m for m in matches if m[1] <= radius_km]
    result = {
        "status": "ok",
        "district": home,
        "radius_km": radius_km,
        "results": [_card(m[3], guest_id, m[1]) for m in nearby[:MAX_RESULTS]],
        "total_nearby": len(nearby),
        "note": SAMPLE_NOTE,
    }
    if not nearby and matches:
        further = sorted(matches, key=lambda m: (m[0], m[1]))[:2]
        result["further_away"] = [_card(m[3], guest_id, m[1]) for m in further]
    return result


def browse_pets(guest_id: str, district: str | None = None, species: str | None = None,
                max_price_inr: int | None = None, trusted_only: bool = False, limit: int = 40) -> dict:
    """The Pets tab grid: every visible pet, trusted first, then nearest, then cheapest."""
    home = resolve_district(district) if district else None
    if district and home is None:
        raise ListingError(f"I don't know the district '{district}' yet.")
    keys = None
    if species and species.strip().lower() not in ("all", "any"):
        keys = _species_keys(species)
        if not keys:
            raise ListingError(f"I don't have listings for '{species}' yet.")
    matches = []
    for lst in deps.get_store().all_listings():
        if not _visible(lst, guest_id) or (keys is not None and lst.get("species_key") not in keys):
            continue
        if max_price_inr is not None and (lst.get("price_inr") or 0) > max_price_inr:
            continue
        if trusted_only and lst["trust_level"] != "TRUSTED":
            continue
        km = _distance(home, lst.get("district")) if home else None
        far = km if km is not None else float("inf")
        matches.append((TRUST_ORDER.get(lst["trust_level"], 2), far, lst.get("price_inr") or 0, km, lst))
    matches.sort(key=lambda m: m[:3])
    return {"status": "ok", "district": home, "total": len(matches),
            "results": [_card(m[4], guest_id, m[3]) for m in matches[:limit]], "note": SAMPLE_NOTE}


def _visible_listing(guest_id: str, listing_id: str) -> dict:
    listing = deps.get_store().get_listing(listing_id)
    if listing is None or not _visible(listing, guest_id):
        raise ListingError("That listing was not found or is not available.")
    return listing


def get_listing(guest_id: str, listing_id: str) -> dict:
    listing = _visible_listing(guest_id, listing_id)
    if listing.get("owner_user_id") and listing["owner_user_id"] != as_viewer(guest_id).user_id:
        listing["views"] = listing.get("views", 0) + 1          # seller dashboard insight
        deps.get_store().save_listing(listing_id, listing)
    breeder = breeders().get(listing.get("breeder_id") or "")
    return {
        "status": "ok",
        "listing": _card(listing, guest_id, None),
        "description": listing["draft"].get("description"),
        "health_notes": listing["draft"].get("health_notes"),
        "checks": listing["screening"]["checks"],
        "questions_to_ask_seller": listing["screening"]["questions_to_ask_seller"],
        "breeder": {"name": breeder["display_name"], "locality": breeder["locality"],
                    "years_experience": breeder["years_experience"], "simulated": True} if breeder else None,
    }


def explain_screening(guest_id: str, listing_id: str) -> dict:
    """The stored trust checks of a listing: any visible listing, or the seller's own in any status."""
    listing = deps.get_store().get_listing(listing_id)
    own = listing is not None and listing.get("owner_user_id") == as_viewer(guest_id).user_id
    if listing is None or not (own or _visible(listing, guest_id)):
        raise ListingError("That listing was not found or is not available.")
    keys = ("trust_level", "trust_score", "checks", "questions_to_ask_seller")
    screening = {key: listing["screening"].get(key, []) for key in keys}
    return {"status": "ok", "listing_id": listing_id, "species": listing["draft"]["species_common"],
            "listing_status": listing["status"], "is_yours": own, "screening": screening}


def create_enquiry(guest_id: str, listing_id: str, message: str) -> dict:
    message = message.strip()
    if not message:
        raise ListingError("Please write a short message for the breeder.")
    if len(message) > MAX_ENQUIRY_CHARS:
        raise ListingError(f"Please keep the message under {MAX_ENQUIRY_CHARS} characters.")
    listing = _visible_listing(guest_id, listing_id)
    store = deps.get_store()
    buyer = as_viewer(guest_id).user_id
    if sum(e.get("buyer_user_id") == buyer for e in store.all_enquiries()) >= MAX_ENQUIRIES_PER_GUEST:
        raise ListingError("You have sent the maximum number of demo enquiries.")
    enquiry_id = f"ENQ_{uuid.uuid4().hex[:10]}"
    store.save_enquiry(enquiry_id, {
        "id": enquiry_id,
        "listing_id": listing_id,
        "breeder_id": listing.get("breeder_id"),
        "listing_owner_user_id": listing.get("owner_user_id"),
        "buyer_user_id": buyer,
        "message": message,
        "demo": True,
        "created_at": _now(),
    })
    return {"status": "ok", "enquiry_id": enquiry_id,
            "note": "Demo: the enquiry is saved to the breeder's inbox in this prototype. "
                    "No SMS or WhatsApp message is sent."}


def my_enquiries(guest_id: str) -> dict:
    """Enquiries received on this guest's own listings (the breeder inbox)."""
    owner = as_viewer(guest_id).user_id
    received = [e for e in deps.get_store().all_enquiries() if e.get("listing_owner_user_id") == owner]
    received.sort(key=lambda e: e["created_at"], reverse=True)
    return {"status": "ok", "enquiries": [_enquiry(e) for e in received]}


def sent_enquiries(guest_id: str) -> dict:
    """Enquiries this customer has sent."""
    buyer = as_viewer(guest_id).user_id
    sent = [e for e in deps.get_store().all_enquiries() if e.get("buyer_user_id") == buyer]
    sent.sort(key=lambda e: e["created_at"], reverse=True)
    return {"status": "ok", "enquiries": [_enquiry(e) for e in sent]}


def _enquiry(e: dict) -> dict:
    """What either side sees: never the other side's login or contact details."""
    return {"enquiry_id": e["id"], "listing_id": e["listing_id"], "message": e["message"],
            "created_at": e["created_at"], "reply": e.get("reply")}


def _received(seller_id: str, enquiry_id: str) -> dict:
    enquiry = deps.get_store().get_enquiry(enquiry_id)
    if enquiry is None or enquiry.get("listing_owner_user_id") != as_viewer(seller_id).user_id:
        raise ListingError("That enquiry was not found.")
    return enquiry


def draft_reply(seller_id: str, enquiry_id: str, farm_name: str | None = None) -> dict:
    """Gemini drafts a reply from the listing's facts; the seller edits and sends it (F8)."""
    from breedernear_core.guardrails import unsafe_reply

    enquiry = _received(seller_id, enquiry_id)
    listing = deps.get_store().get_listing(enquiry["listing_id"]) or {}
    d = listing.get("draft", {})
    warnings = [c["detail"] for c in listing.get("screening", {}).get("checks", []) if c["result"] == "warn"]
    facts = "\n".join(f"{k}: {v}" for k, v in [
        ("Farm name", farm_name or listing.get("breeder_name") or "our farm"),
        ("Listing status", listing.get("status")), ("Species", d.get("species_common")),
        ("Variety", d.get("variety")), ("Count", d.get("count")), ("Sold per", d.get("unit")),
        ("Age (months)", d.get("age_months")), ("Price per unit (INR)", d.get("price_inr")),
        ("Area", ", ".join(x for x in [d.get("locality"), d.get("district")] if x)),
        ("Health notes", d.get("health_notes")), ("Description", d.get("description")),
        ("Trust check warnings", "; ".join(warnings) or "none"),
    ] if v not in (None, "")) + f"\n\nBuyer's message:\n{enquiry['message']}"
    result = deps.get_vision().write_reply(facts)
    text = result.reply.strip()
    if unsafe_reply(text) or not text:
        text = ("Thank you for your interest. You are welcome to visit and see the animals and their "
                f"parents before deciding. I will confirm the details soon. - {farm_name or 'our farm'}")
    return {"status": "ok", "enquiry_id": enquiry_id, "reply": text[:MAX_REPLY_CHARS],
            "needs_seller_input": result.needs_seller_input[:5]}


def send_reply(seller_id: str, enquiry_id: str, text: str) -> dict:
    text = text.strip()
    if not text:
        raise ListingError("Please write a reply first.")
    if len(text) > MAX_REPLY_CHARS:
        raise ListingError(f"Please keep the reply under {MAX_REPLY_CHARS} characters.")
    enquiry = _received(seller_id, enquiry_id)
    enquiry["reply"] = {"text": text, "created_at": _now()}
    deps.get_store().save_enquiry(enquiry_id, enquiry)
    return {"status": "ok", "enquiry": _enquiry(enquiry)}
