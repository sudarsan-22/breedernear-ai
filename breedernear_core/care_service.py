"""Starter kits, first-14-days care plans and the demo cart.

Product choice and cage sizes are decided in code (welfare rules); Gemini only writes the care plan,
and code adds the disclaimer and removes anything that looks like medicine dosing.
"""

import re
from datetime import UTC, datetime

from pydantic import ValidationError

from breedernear_core import deps
from breedernear_core.data import load_seed
from breedernear_core.listing_service import ListingError
from breedernear_core.safety.species_rules import find_protected, species_key_for
from breedernear_core.safety.welfare_rules import cage_is_big_enough, min_cage_cm

MAX_KIT_ITEMS = 8
MAX_QUANTITY = 10
DISCLAIMER = "This is general guidance, not veterinary advice. Consult a vet if you're worried."
DEMO_NOTE = "Sample products from fictional brands. Demo cart only: no payments or orders."
KIT_CATEGORIES = {
    "bird": ["cage", "food", "perches", "feeders", "mineral", "carrier", "treat", "toy"],
    "dog": ["food", "bowls", "bed", "collar_leash", "toy", "grooming", "hygiene", "carrier"],
    "cat": ["food", "litter_box", "litter", "scratching_post", "bowls", "grooming", "bed", "carrier"],
}
WHY = {
    "food": "Right food for this species from day one.",
    "perches": "Different perch sizes keep feet healthy.",
    "feeders": "Separate cups for seed, water and greens.",
    "mineral": "Calcium source and beak care.",
    "carrier": "Safe, ventilated transport home and to the vet.",
    "treat": "Helps with taming and trust.",
    "toy": "Play and exercise to prevent boredom.",
    "bowls": "Stable bowls for food and fresh water.",
    "bed": "A sized bed gives a quiet place to rest.",
    "collar_leash": "Needed for safe walks and early training.",
    "grooming": "Regular brushing suited to this coat.",
    "hygiene": "Gentle, non-medicated cleaning.",
    "litter_box": "A covered box helps with litter training.",
    "litter": "Low-dust litter for the box.",
    "scratching_post": "Protects furniture and keeps claws healthy.",
}
# Lines that look like medicine dosing are dropped from generated care plans.
_MEDICAL = re.compile(r"\b\d+(\.\d+)?\s?(mg|ml|mcg|iu)\b|\bdos(e|age|ing)\b|\bantibiotic|\bivermectin\b"
                      r"|\benrofloxacin\b|\bmetronidazole\b|\bdoxycycline\b", re.IGNORECASE)
_care_cache: dict[tuple[str, int], dict] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _products() -> list[dict]:
    return load_seed("products.json")["products"]


def _species_entry(species: str) -> dict:
    if find_protected(species):
        raise ListingError("That is a protected native species: BreederNear can't help with keeping it.")
    key = species_key_for(species)
    for sp in load_seed("species.json")["species"]:
        if sp["key"] == key:
            return sp
    names = ", ".join(sp["name"] for sp in load_seed("species.json")["species"])
    raise ListingError(f"I don't have care data for '{species}' yet. Available: {names}.")


def _cm(dims) -> str:
    return "×".join(str(d) for d in dims) + " cm"


def build_starter_kit(species: str, count: int) -> dict:
    sp = _species_entry(species)
    count = max(1, min(int(count), 20))
    key = sp["key"]
    required = min_cage_cm(key, count)
    items, too_small = [], []
    for category in KIT_CATEGORIES[sp["group"]]:
        candidates = [p for p in _products()
                      if p["category"] == category and key in p["species"] and p["stock"] > 0]
        if category == "cage":
            too_small = [p["name"] for p in candidates
                         if not cage_is_big_enough(tuple(p["dimensions_cm"]), key, count)]
            candidates = [p for p in candidates if cage_is_big_enough(tuple(p["dimensions_cm"]), key, count)]
        if not candidates:
            continue
        product = min(candidates, key=lambda p: p["price_inr"])
        why = (f"Meets the minimum size for {count} {sp['name']} ({_cm(required)})." if category == "cage"
               else WHY.get(category, ""))
        items.append({"product_id": product["id"], "name": product["name"], "brand": product["brand"],
                      "category": category, "price_inr": product["price_inr"], "quantity": 1, "why": why})
    items = items[:MAX_KIT_ITEMS]
    result = {
        "status": "ok",
        "species": sp["name"],
        "count": count,
        "items": items,
        "total_inr": sum(i["price_inr"] * i["quantity"] for i in items),
        "note": DEMO_NOTE,
    }
    if required:
        result["min_cage_cm"] = list(required)
        result["cages_excluded_as_too_small"] = too_small
        if not any(i["category"] == "cage" for i in items):
            result["welfare_note"] = (f"No cage in the catalogue meets the minimum {_cm(required)} for "
                                      f"{count} birds. Consider an aviary or fewer birds.")
    return result


def _clean(lines: list[str]) -> list[str]:
    return [line for line in lines if not _MEDICAL.search(line)]


def care_plan(species: str, age_months: int | None = None) -> dict:
    sp = _species_entry(species)
    age = age_months if age_months is not None and age_months >= 0 else -1
    cache_key = (sp["key"], min(age, 12))
    if cache_key in _care_cache:
        return _care_cache[cache_key]
    facts = (f"Species: {sp['name']} ({sp['group']}). Typical lifespan: {sp['lifespan_years'][0]} to "
             f"{sp['lifespan_years'][1]} years. Noise: {sp['noise']}. Care time: about {sp['daily_minutes']} "
             f"minutes a day. Watch-outs: {' '.join(sp['watch_outs'])}"
             + (f" Age of the new pet: {age} months." if age >= 0 else ""))
    try:
        plan = deps.get_vision().write_care_plan(facts)
    except ValidationError as e:
        raise ListingError("I couldn't write a complete care plan just now. Please ask again.") from e
    data = plan.model_dump()
    for phase in data["phases"]:
        phase["steps"] = _clean(phase["steps"])
    data["diet"] = _clean(data["diet"])
    data["daily_routine"] = _clean(data["daily_routine"])
    data["see_vet_if"] = _clean(data["see_vet_if"])
    if len(data["see_vet_if"]) < 3:
        raise ListingError("I couldn't write a complete care plan just now. Please ask again.")
    data["species"] = sp["name"]
    data["disclaimer"] = DISCLAIMER
    result = {"status": "ok", "care_plan": data}
    _care_cache[cache_key] = result
    return result


def _product(product_id: str) -> dict:
    for p in _products():
        if p["id"] == product_id:
            return p
    raise ListingError(f"Product {product_id} was not found.")


def view_cart(guest_id: str) -> dict:
    cart = deps.get_store().get_cart(guest_id) or {"items": []}
    lines = []
    for item in cart["items"]:
        p = _product(item["product_id"])
        lines.append({"product_id": p["id"], "name": p["name"], "brand": p["brand"],
                      "price_inr": p["price_inr"], "quantity": item["quantity"],
                      "line_total_inr": p["price_inr"] * item["quantity"]})
    return {"status": "ok", "items": lines, "total_inr": sum(x["line_total_inr"] for x in lines),
            "note": DEMO_NOTE}


def add_to_cart(guest_id: str, product_ids: list[str], quantity: int = 1) -> dict:
    if not product_ids:
        raise ListingError("Tell me which products to add.")
    if not 1 <= quantity <= MAX_QUANTITY:
        raise ListingError(f"Quantity must be between 1 and {MAX_QUANTITY}.")
    store = deps.get_store()
    cart = store.get_cart(guest_id) or {"items": []}
    current = {i["product_id"]: i["quantity"] for i in cart["items"]}
    for product_id in product_ids:
        p = _product(product_id)
        wanted = current.get(product_id, 0) + quantity
        if wanted > min(p["stock"], MAX_QUANTITY):
            raise ListingError(f"Only {min(p['stock'], MAX_QUANTITY)} of {p['name']} can be added.")
        current[product_id] = wanted
    store.save_cart(guest_id, {"items": [{"product_id": k, "quantity": v} for k, v in current.items()],
                               "updated_at": _now()})
    return view_cart(guest_id)


def remove_from_cart(guest_id: str, product_id: str) -> dict:
    store = deps.get_store()
    cart = store.get_cart(guest_id) or {"items": []}
    cart["items"] = [i for i in cart["items"] if i["product_id"] != product_id]
    cart["updated_at"] = _now()
    store.save_cart(guest_id, cart)
    return view_cart(guest_id)
