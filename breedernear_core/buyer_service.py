"""Buyer profile, compatibility %, the AI-drafted first message, and the scam shield on messages (F16, F17).

Gemini turns the buyer's own words into a profile and drafts text. The compatibility % is calculated in code
from the same rules as the "Which pet suits me?" quiz, so it is explainable and repeatable: a species the
rules exclude scores 0 with the rule's reason.
"""

import re
from datetime import UTC, datetime

from breedernear_core import deps
from breedernear_core.guardrails import unsafe_reply
from breedernear_core.listing_service import ListingError
from breedernear_core.match_service import GROUP_WORDS, SPACE_RANK, _species, _visible_listing, as_viewer
from breedernear_core.safety.price_rules import price_range
from breedernear_core.safety.scam_rules import find_scam_signals
from breedernear_core.schemas import BuyerProfile

PROFILES = "buyer_profiles"
MAX_WORDS_CHARS = 1000
_MESSAGE_SIGNALS = [
    (
        "asks for an OTP, PIN or bank details",
        re.compile(r"\botp\b|\bcvv\b|\bupi\s*pin\b|\bbank\s*details\b|\baccount\s*number\b", re.I),
    )
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------- profile
def get_profile(user_id: str) -> dict:
    record = deps.get_store().fetch(PROFILES, user_id)
    return {
        "status": "ok",
        "profile": record["profile"] if record else None,
        "words": record.get("words") if record else None,
    }


def save_profile(user_id: str, profile: dict | None = None, words: str | None = None) -> dict:
    """Save from the quiz fields, from the buyer's own words (read by Gemini), or both (fields win)."""
    words = (words or "").strip()[:MAX_WORDS_CHARS]
    if not profile and not words:
        raise ListingError("Tell us a little about your home, or answer the quiz.")
    base = deps.get_vision().read_profile(words).model_dump() if words else BuyerProfile().model_dump()
    try:
        given = {k: v for k, v in (profile or {}).items() if v is not None}
        clean = BuyerProfile(**(base | given)).model_dump()
    except ValueError as e:
        raise ListingError("Some answers look wrong. Please check them.") from e
    deps.get_store().put(
        PROFILES,
        user_id,
        {"user_id": user_id, "profile": clean, "words": words or None, "updated_at": _now()},
    )
    return {"status": "ok", "profile": clean, "compatibility": compatibility(user_id)["species"]}


# ---------------------------------------------------------------- compatibility (code, not the model)
def score_species(sp: dict, p: dict) -> tuple[int, list[str], list[str]]:
    """Return (percent, reasons for, watch-outs). 0 % when a hard rule excludes the species."""
    rng = price_range(sp["key"])
    is_flat = p["home_type"] == "flat"
    hard = []
    if p["animal_group"] in GROUP_WORDS and sp["group"] != p["animal_group"]:
        hard.append(f"you're looking for a {p['animal_group']}")
    if p.get("budget_inr") and rng and rng[0] > p["budget_inr"]:
        hard.append(f"usually costs ₹{rng[0]:,} or more")
    if SPACE_RANK[sp["space_needed"]] > SPACE_RANK["medium" if is_flat else "large"]:
        hard.append("needs more space than a flat")
    if not p["noise_ok"] and sp["noise"] == "high":
        hard.append("can be noisy")
    if p["time_per_day_minutes"] < sp["daily_minutes"] * 0.75:
        hard.append(f"needs about {sp['daily_minutes']} minutes of care a day")
    if hard:
        return 0, [], hard

    score, pros, cons = 60, [f"fits a {'flat' if is_flat else 'house'}"], []

    def adjust(points: int, reason: str) -> None:
        nonlocal score
        score += points
        (pros if points > 0 else cons).append(reason)

    if p["first_time_owner"]:
        if sp["beginner_friendly"]:
            adjust(10, "easy for a first-time owner")
        else:
            adjust(-15, "better for experienced owners")
    if p["has_young_children"]:
        if sp["kid_friendly"]:
            adjust(10, "gentle with children")
        else:
            adjust(-15, "better with older children")
    if sp["noise"] == "low":
        adjust(5, "quiet")
    if p["time_per_day_minutes"] >= sp["daily_minutes"] * 1.5:
        adjust(5, "you have time to spare for it")
    if sp["group"] == "dog":
        away = p.get("hours_away_per_day", 8)
        if away >= 9:
            adjust(-15, f"a dog alone for {away} hours a day gets lonely")
        activity = p.get("activity", "medium")
        if activity == "high":
            adjust(10, "matches your active family")
        elif activity == "low":
            adjust(-10, "needs daily walks and play")
    if p.get("allergies"):
        adjust(
            -{"cat": 25, "dog": 15}.get(sp["group"], 10),
            "feather dust can trigger allergies" if sp["group"] == "bird" else "can trigger pet allergies",
        )
    if p.get("budget_inr") and rng and rng[1] <= p["budget_inr"]:
        adjust(5, "well within your budget")
    return max(5, min(98, score)), pros, cons


def compatibility(user_id: str) -> dict:
    record = deps.get_store().fetch(PROFILES, user_id)
    if not record:
        return {
            "status": "ok",
            "species": [],
            "note": "Save your profile to see how well each pet suits you.",
        }
    out = []
    for sp in _species():
        pct, pros, cons = score_species(sp, record["profile"])
        out.append(
            {
                "species_key": sp["key"],
                "species": sp["name"],
                "group": sp["group"],
                "percent": pct,
                "reasons": pros,
                "watch_outs": cons,
            }
        )
    out.sort(key=lambda r: -r["percent"])
    return {
        "status": "ok",
        "species": out,
        "note": "Calculated from sample care guidance: space, time, noise, family, budget and allergies.",
    }


def percent_for(user_id: str, species_key: str | None) -> int | None:
    record = deps.get_store().fetch(PROFILES, user_id) if species_key else None
    sp = next((s for s in _species() if s["key"] == species_key), None) if record else None
    return score_species(sp, record["profile"])[0] if sp else None


# ---------------------------------------------------------------- first message and scam shield
def opening_message(user_id, listing_id: str) -> dict:
    """user_id: an account ID or a Viewer (account + device), as the other buyer functions take."""
    viewer = as_viewer(user_id)
    listing = _visible_listing(viewer, listing_id)
    d = listing["draft"]
    profile = (deps.get_store().fetch(PROFILES, viewer.user_id) or {}).get("profile") or {}
    facts = "\n".join(
        f"{k}: {v}"
        for k, v in [
            ("Species", d.get("species_common")),
            ("Variety", d.get("variety")),
            ("Age (months)", d.get("age_months")),
            ("Price (INR)", listing.get("price_inr")),
            ("Sold per", d.get("unit")),
            ("Area", d.get("locality")),
            ("Dog", "yes" if d.get("animal_group") == "dog" else None),
            ("Buyer's home", profile.get("home_type")),
            ("Young children", "yes" if profile.get("has_young_children") else None),
            ("First-time owner", "yes" if profile.get("first_time_owner") else None),
        ]
        if v not in (None, "")
    )
    text = deps.get_vision().opening_message(facts).message.strip()
    if not text or unsafe_reply(text) or scan_text(text, use_model=False)["risk"] != "none":
        name = (d.get("species_common") or "pet").lower()
        text = f"Hello! Is your {name} still available? Could I visit to see it and its parents this week?"
    return {"status": "ok", "message": text[:500]}


def scan_text(text: str, use_model: bool = True) -> dict:
    """Fixed scam rules, plus Gemini when available. If Gemini fails, the rules still work."""
    signals = list(find_scam_signals(text))
    signals += [label for label, rx in _MESSAGE_SIGNALS if rx.search(text or "")]
    risk = "high" if signals else "none"
    if use_model and text and text.strip():
        try:
            scan = deps.get_vision().scan_message(text)
            signals += [s for s in scan.signals if s.lower() not in {x.lower() for x in signals}][:3]
            risk = max(risk, scan.risk, key=["none", "low", "high"].index)
        except Exception:  # noqa: BLE001 - the rules above are the safety floor
            pass
    return {"risk": risk, "signals": signals[:5]}
