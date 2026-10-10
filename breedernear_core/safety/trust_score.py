"""Deterministic trust scoring for listings. The LLM supplies observations; this code decides.

Formula: docs/implementation/02-agent-design.md#trust-score-formula-safetytrust_scorepy
"""

from dataclasses import dataclass

from breedernear_core.safety.price_rules import assess_price
from breedernear_core.safety.scam_rules import find_scam_signals
from breedernear_core.safety.species_rules import find_cites, find_protected
from breedernear_core.schemas import Check, ListingDraft, PhotoScreen, Screening

TRUSTED_MIN_SCORE = 75
MAJOR_PENALTY = 25
PROTECTED_VISION_CONFIDENCE = 0.5


@dataclass
class ScreeningInputs:
    draft: ListingDraft
    raw_text: str = ""
    photo: PhotoScreen | None = None
    duplicate_of: str | None = None          # listing ID whose photo matches
    price_range: tuple[int, int] | None = None
    sawb_status: str | None = None           # "valid" | "expired" | "unknown" | "missing" (dogs)


def screen(inputs: ScreeningInputs) -> Screening:
    d, photo = inputs.draft, inputs.photo
    checks: list[Check] = []
    questions: list[str] = []

    # 1. Protected native species: text OR vision is enough to block.
    # Uses the breeder's own words and extracted species fields, not the model-written summary.
    protected = find_protected(inputs.raw_text, d.species_common, d.species_scientific or "",
                               d.variety or "")
    vision_protected = (photo is not None and photo.possibly_protected_native_species
                        and photo.species_guess_confidence >= PROTECTED_VISION_CONFIDENCE)
    if photo is not None:
        protected += find_protected(photo.species_guess)
    if protected or vision_protected:
        name = protected[0].common_name if protected else "a protected native species"
        checks.append(Check(name="protected_species", result="block",
                            detail=f"Looks like {name}. Trading protected Indian native species is "
                                   "illegal under the Wild Life (Protection) Act, 1972."))
        return Screening(trust_score=0, trust_level="BLOCKED", checks=checks)
    checks.append(Check(name="protected_species", result="pass",
                        detail="Not a protected native species."))

    # 2. Photo-based checks.
    if photo is not None:
        if photo.image_quality == "not_animal":
            checks.append(Check(name="photo", result="warn", penalty=10,
                                detail="The photo doesn't show the animal being sold."))
        elif photo.image_quality == "poor" or photo.looks_like_stock_or_watermarked:
            checks.append(Check(name="photo", result="warn", penalty=10,
                                detail="Photo is unclear or looks like a stock/watermarked image."))
            questions.append("Ask for a fresh photo or video call showing the animals today.")
        else:
            checks.append(Check(name="photo", result="pass", detail="Clear photo of the animal."))
        if photo.possible_dye_or_disguise:
            checks.append(Check(name="dye", result="warn", penalty=30,
                                detail="Colours look unnatural: the bird may be dyed or disguised."
                                       + (f" ({photo.dye_evidence})" if photo.dye_evidence else "")))
        for sign in photo.visible_health_signs[:2]:
            checks.append(Check(name="health_sign", result="warn", penalty=15,
                                detail=f"Visible sign to ask about: {sign}."))
            questions.append(f"Ask the seller about: {sign}.")
    if not d.photo_text_consistent:
        checks.append(Check(name="photo_text_match", result="warn", penalty=15,
                            detail="The photo doesn't seem to match the species in the text."))

    # 3. Reused photo (perceptual hash match found by the caller).
    if inputs.duplicate_of:
        checks.append(Check(name="duplicate_photo", result="warn", penalty=35,
                            detail="The same photo is used in another listing."))
        questions.append("Ask for a new photo of these exact animals with today's date on paper.")

    # 4. Price.
    checks.append(assess_price(d.price_inr, inputs.price_range))

    # 5. Scam language.
    signals = find_scam_signals(inputs.raw_text)
    if signals:
        checks.append(Check(name="scam_language", result="warn", penalty=30,
                            detail="Warning signs in the text: " + "; ".join(signals) + "."))
        questions.append("Never pay the full amount before seeing the animal in person.")

    # 6. Dog breeder registration (PCA Dog Breeding and Marketing Rules, 2017).
    if d.animal_group == "dog":
        status = inputs.sawb_status or "missing"
        if status == "valid":
            checks.append(Check(name="sawb_registration", result="pass",
                                detail="Dog-breeder registration found (simulated registry)."))
        elif status == "missing":
            checks.append(Check(name="sawb_registration", result="warn", penalty=25,
                                detail="No State Animal Welfare Board breeder registration given."))
            questions.append("Ask for the breeder's State Animal Welfare Board registration.")
        else:
            checks.append(Check(name="sawb_registration", result="warn", penalty=30,
                                detail="Registration number not found or expired (simulated registry)."))

    # 7. CITES exotics need PARIVESH registration.
    cites = find_cites(inputs.raw_text, d.species_common, d.species_scientific or "", d.variety or "")
    if cites and not d.parivesh_registration_id:
        # Major penalty: a CITES species without a registration is capped at CAUTION.
        checks.append(Check(name="parivesh", result="warn", penalty=MAJOR_PENALTY,
                            detail=f"{cites[0].common_name} is CITES-listed: possession and transfer "
                                   "must be registered on PARIVESH 2.0. No registration ID given."))
        questions.append("Ask for the PARIVESH registration of the bird and its parents.")

    score = max(0, 100 - sum(c.penalty for c in checks))
    has_major = any(c.result == "warn" and c.penalty >= MAJOR_PENALTY for c in checks)
    level = "TRUSTED" if score >= TRUSTED_MIN_SCORE and not has_major else "CAUTION"
    return Screening(trust_score=score, trust_level=level, checks=checks,
                     questions_to_ask_seller=list(dict.fromkeys(questions)))
