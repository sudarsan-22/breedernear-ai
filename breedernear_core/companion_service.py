"""Pet care companion (F20): My pets, a daily log with Gemini feedback, growth, a health calendar and a
symptom checker.

Gemini reviews the day's food and play and gives a symptom's urgency in plain words. Code decides the
rest: weight ranges, the vaccination and deworming outline (data/seed/pet_care.json, general guidance),
streaks, check-in prompts, and an emergency floor for red-flag words. Every Gemini text passes the reply
guard: never a medicine name, dose or diagnosis; always a vet for health worries.
"""

import re
import uuid
from datetime import UTC, date, datetime, timedelta

from breedernear_core import deps
from breedernear_core.data import load_seed
from breedernear_core.guardrails import MEDICINE_REPLY, unsafe_reply
from breedernear_core.listing_service import ListingError

PETS, LOGS, WEIGHTS = "pets", "pet_logs", "pet_weights"
MAX_TEXT = 400
DISCLAIMER = "General guidance, not veterinary advice. When in doubt, see a vet (an avian vet for birds)."
EMERGENCY_WORDS = re.compile(
    r"breath|gasp|bleed|blood|seiz|fit|collaps|unconscious|poison|chocolate|rat\s*poison|can'?t\s*stand|"
    r"tail\s*bob|swollen\s*belly|no\s*urine|not\s*peeing|straining",
    re.I,
)
VET_SOON_WORDS = re.compile(
    r"not\s*eat|stopped\s*eating|vomit|diarr|watery\s*dropping|limp|discharge|fluff", re.I
)


def _now() -> datetime:
    return datetime.now(UTC)


def _care() -> dict:
    return load_seed("pet_care.json")


def _clip(text: str | None) -> str:
    return (text or "").strip()[:MAX_TEXT]


# ---------------------------------------------------------------- pets
def start_pet(owner_id: str, listing: dict, sale_id: str, name: str | None = None) -> dict:
    d = listing.get("draft", {})
    pet_id = f"PET_{uuid.uuid4().hex[:10]}"
    pet = {
        "id": pet_id,
        "owner_id": owner_id,
        "name": (name or "").strip()[:30] or d.get("species_common", "My pet"),
        "species_key": listing.get("species_key"),
        "species": d.get("species_common"),
        "variety": d.get("variety"),
        "group": d.get("animal_group") or "bird",
        "age_months_at_home": d.get("age_months"),
        "home_date": _now().date().isoformat(),
        "listing_id": listing.get("id"),
        "sale_id": sale_id,
        "created_at": _now().isoformat(),
    }
    deps.get_store().put(PETS, pet_id, pet)
    return pet


def _own_pet(owner_id: str, pet_id: str) -> dict:
    pet = deps.get_store().fetch(PETS, pet_id)
    if pet is None or pet["owner_id"] != owner_id:
        raise ListingError("That pet was not found.")
    return pet


def list_pets(owner_id: str) -> dict:
    pets = sorted(deps.get_store().find(PETS, owner_id=owner_id), key=lambda p: p["created_at"])
    return {"status": "ok", "pets": [_summary(p) for p in pets]}


def _age_months(pet: dict, today: date) -> float | None:
    if pet.get("age_months_at_home") is None:
        return None
    days = (today - date.fromisoformat(pet["home_date"])).days
    return pet["age_months_at_home"] + days / 30.4


def _summary(pet: dict, today: date | None = None) -> dict:
    today = today or _now().date()
    day = (today - date.fromisoformat(pet["home_date"])).days
    return {
        "pet_id": pet["id"],
        "name": pet["name"],
        "species": pet["species"],
        "variety": pet.get("variety"),
        "group": pet["group"],
        "days_home": day,
        "home_date": pet["home_date"],
        "age_months": round(_age_months(pet, today), 1) if _age_months(pet, today) is not None else None,
        "streak": _streak(pet["id"], today),
    }


def _logs(pet_id: str) -> list[dict]:
    return sorted(deps.get_store().find(LOGS, pet_id=pet_id), key=lambda r: r["at"], reverse=True)


def _weights(pet_id: str) -> list[dict]:
    return sorted(deps.get_store().find(WEIGHTS, pet_id=pet_id), key=lambda r: r["at"])


def _streak(pet_id: str, today: date) -> int:
    days = {date.fromisoformat(r["day"]) for r in _logs(pet_id)}
    start = today if today in days else today - timedelta(days=1)
    n = 0
    while start - timedelta(days=n) in days:
        n += 1
    return n


def get_pet(owner_id: str, pet_id: str, today: date | None = None) -> dict:
    pet = _own_pet(owner_id, pet_id)
    today = today or _now().date()
    weights = _weights(pet_id)
    return {
        "status": "ok",
        "pet": _summary(pet, today),
        "logs": _logs(pet_id)[:14],
        "weights": [w | {"range": weight_range(pet, date.fromisoformat(w["day"]))} for w in weights][-20:],
        "typical_weight": weight_range(pet, today),
        "check_in": check_in(pet, today),
        "calendar": calendar(pet),
        "deworming": _care()["deworming"].get(pet["group"], ""),
        "red_flags": _care()["red_flags"].get(pet["group"], []),
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------- growth, calendar, check-in (code)
def weight_range(pet: dict, when: date) -> dict | None:
    info = _care()["weights"].get(pet.get("species_key") or "")
    if not info:
        return None
    if "adult" in info:
        lo, hi = info["adult"]
        return {"unit": info["unit"], "low": lo, "high": hi, "label": "typical adult weight"}
    age = _age_months(pet, when)
    if age is None:
        return None
    keys = sorted(int(k) for k in info["by_age_months"])
    key = max([k for k in keys if k <= age] or [keys[0]])
    lo, hi = info["by_age_months"][str(key)]
    return {"unit": info["unit"], "low": lo, "high": hi, "label": f"typical at about {key} months"}


def calendar(pet: dict) -> list[dict]:
    plan = _care()["vaccination"].get(pet["group"], [])
    if pet["group"] == "bird":
        return [{"what": p["what"], "due": None, "status": "advice"} for p in plan]
    if pet.get("age_months_at_home") is None:
        return [{"what": p["what"], "due": None, "status": "ask your vet"} for p in plan]
    born = date.fromisoformat(pet["home_date"]) - timedelta(days=round(pet["age_months_at_home"] * 30.4))
    today = _now().date()
    out = []
    for p in plan:
        due = born + timedelta(weeks=p["age_weeks"])
        status = (
            "check the record"
            if due < date.fromisoformat(pet["home_date"])
            else ("due" if due <= today + timedelta(days=14) else "upcoming")
        )
        out.append(
            {"what": p["what"], "due": due.isoformat() if pet["group"] != "bird" else None, "status": status}
        )
    return out


def check_in(pet: dict, today: date) -> str:
    """This week's prompt, chosen by code from the recent logs and weights."""
    logs, weights = _logs(pet["id"]), _weights(pet["id"])
    recent = [r for r in logs if (today - date.fromisoformat(r["day"])).days < 7]
    if any(not r.get("food_ok", True) for r in recent[:3]):
        return (f"A recent food may not suit {pet['name']}. Check the tips below, and see a vet if anything "
                "seems off.")
    if not weights or (today - date.fromisoformat(weights[-1]["day"])).days >= 7:
        return f"Weigh {pet['name']} this week and add it to the growth tracker."
    if len(recent) < 3:
        return f"Log {pet['name']}'s food and play each day: small changes are easier to spot early."
    return f"Great routine! {pet['name']} has a {_streak(pet['id'], today)}-day log streak."


# ---------------------------------------------------------------- daily log (Gemini feedback)
def _safe_texts(*texts: str) -> bool:
    return not any(unsafe_reply(t) for t in texts if t)


def log_day(
    owner_id: str,
    pet_id: str,
    food: str = "",
    play: str = "",
    note: str = "",
    photo_upload_id: str | None = None,
) -> dict:
    pet = _own_pet(owner_id, pet_id)
    food, play, note = _clip(food), _clip(play), _clip(note)
    if not (food or play or note or photo_upload_id):
        raise ListingError("Add what they ate, how they played, or a note.")
    images = []
    if photo_upload_id:
        found = deps.get_uploads().get(owner_id, photo_upload_id)
        if found is None:
            raise ListingError("That photo was not found. Please upload it again.")
        images = [found]
    age = _age_months(pet, _now().date())
    facts = (
        f"Species: {pet['species']} ({pet['group']}). "
        f"Age: {round(age) if age is not None else 'unknown'} months. "
        f"Food today: {food or 'not logged'}. Play today: {play or 'not logged'}. Note: {note or 'none'}."
    )
    review = deps.get_vision().review_daily_log(facts, images)
    feedback, tips = review.feedback, review.suggestions[:3]
    if not _safe_texts(feedback, *tips):
        feedback, tips = MEDICINE_REPLY, []
    if photo_upload_id:
        deps.get_uploads().delete(owner_id, photo_upload_id)  # keep the result, not the photo
    now = _now()
    log_id = f"LOG_{uuid.uuid4().hex[:10]}"
    entry = {
        "id": log_id,
        "pet_id": pet_id,
        "owner_id": owner_id,
        "day": now.date().isoformat(),
        "at": now.isoformat(),
        "food": food,
        "play": play,
        "note": note,
        "had_photo": bool(photo_upload_id),
        "food_ok": review.food_ok,
        "feedback": feedback,
        "suggestions": tips,
    }
    deps.get_store().put(LOGS, log_id, entry)
    return {"status": "ok", "log": entry, "streak": _streak(pet_id, now.date()), "disclaimer": DISCLAIMER}


def add_weight(owner_id: str, pet_id: str, value: float) -> dict:
    pet = _own_pet(owner_id, pet_id)
    rng = weight_range(pet, _now().date())
    unit = rng["unit"] if rng else ("g" if pet["group"] == "bird" else "kg")
    if not 0 < value < (5000 if unit == "g" else 120):
        raise ListingError(f"Please enter the weight in {unit}.")
    now = _now()
    entry_id = f"WGT_{uuid.uuid4().hex[:10]}"
    entry = {
        "id": entry_id,
        "pet_id": pet_id,
        "owner_id": owner_id,
        "value": value,
        "unit": unit,
        "day": now.date().isoformat(),
        "at": now.isoformat(),
    }
    deps.get_store().put(WEIGHTS, entry_id, entry)
    if not rng:
        verdict = "Saved. Ask your vet what a healthy weight is for your pet."
    elif value < rng["low"]:
        verdict = (f"Below the {rng['label']} ({rng['low']}–{rng['high']} {unit}). "
                   "Show your vet if it keeps dropping.")
    elif value > rng["high"]:
        verdict = (f"Above the {rng['label']} ({rng['low']}–{rng['high']} {unit}). "
                   "Ask your vet about diet and exercise.")
    else:
        verdict = f"Within the {rng['label']} ({rng['low']}–{rng['high']} {unit})."
    return {"status": "ok", "weight": entry, "range": rng, "verdict": verdict}


# ---------------------------------------------------------------- symptom checker (strict)
def check_symptoms(owner_id: str, pet_id: str, text: str) -> dict:
    pet = _own_pet(owner_id, pet_id)
    text = _clip(text)
    if len(text) < 3:
        raise ListingError("Describe what you notice, for example 'sneezing since yesterday'.")
    age = _age_months(pet, _now().date())
    result = deps.get_vision().check_symptom(
        f"Pet: {pet['species']} ({pet['group']}), "
        f"about {round(age) if age is not None else '?'} months old.\n"
        f"What the owner notices: {text}"
    )
    urgency = result.urgency
    if EMERGENCY_WORDS.search(text):  # code floor: red flags are urgent
        urgency = "emergency"
    elif urgency == "monitor" and (VET_SOON_WORDS.search(text) or pet["group"] == "bird"):
        urgency = "vet_soon"  # birds hide illness
    meaning, watch, do_now = result.possible_meaning, result.watch_for[:5], result.do_now[:5]
    if not _safe_texts(meaning, *watch, *do_now):
        meaning, watch, do_now = MEDICINE_REPLY, [], []
    first = {
        "emergency": "Go to a vet now (an avian vet for birds), or call one on the way.",
        "vet_soon": "Book a vet visit within a day or two (an avian vet for birds).",
        "monitor": "Watch closely at home; see a vet if it continues or gets worse.",
    }[urgency]
    return {
        "status": "ok",
        "urgency": urgency,
        "first_step": first,
        "possible_meaning": meaning,
        "watch_for": watch,
        "do_now": do_now,
        "red_flags": _care()["red_flags"].get(pet["group"], []),
        "disclaimer": DISCLAIMER,
    }
