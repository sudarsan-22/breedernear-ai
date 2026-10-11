"""Structured data shared by agents, tools and the API. See docs/implementation/02-agent-design.md."""

from typing import Literal

from pydantic import BaseModel, Field

AnimalGroup = Literal["bird", "dog", "cat", "other"]
TrustLevel = Literal["TRUSTED", "CAUTION", "BLOCKED"]
CheckResult = Literal["pass", "warn", "block", "info"]


class ListingDraft(BaseModel):
    """A listing extracted from a breeder's photos and casual message."""

    species_common: str
    species_scientific: str | None = None
    variety: str | None = None
    animal_group: AnimalGroup
    count: int = Field(ge=1, default=1, description=(
        "How many sale units are offered, counted in `unit`: '4 pairs' -> 4; '2 chicks' -> 2; "
        "'a litter of 6 puppies' -> 6."))
    unit: Literal["single", "pair", "litter"] = Field(default="single", description=(
        "'pair' if priced per pair (jodi), 'litter' only if the whole litter has one price, else 'single'."))
    sex: str | None = None
    age_months: int | None = Field(default=None, ge=0)
    price_inr: int | None = Field(default=None, gt=0, description="Price per unit in rupees, digits only.")
    district: str | None = None
    locality: str | None = None
    health_notes: str | None = None
    sawb_registration_no: str | None = None
    parivesh_registration_id: str | None = None
    description: str = ""
    language_detected: str = "en"
    photo_text_consistent: bool = True
    missing_fields: list[str] = Field(default=[], description=(
        "Buyer-relevant fields not stated, from: price_inr, age_months, health_notes, district."))
    confidence: float = Field(default=0.0, ge=0, le=1)


class PhotoScreen(BaseModel):
    """What Gemini vision observed in a listing's photos."""

    species_guess: str
    species_guess_confidence: float = Field(ge=0, le=1)
    possibly_protected_native_species: bool = False
    possible_dye_or_disguise: bool = False
    dye_evidence: str | None = None
    visible_health_signs: list[str] = []
    housing_observations: list[str] = []
    image_quality: Literal["good", "poor", "not_animal"] = "good"
    looks_like_stock_or_watermarked: bool = False


class Check(BaseModel):
    name: str
    result: CheckResult
    detail: str
    penalty: int = 0


class Screening(BaseModel):
    """Trust decision for a listing. Computed in code (safety/trust_score.py), never by the LLM."""

    trust_score: int = Field(ge=0, le=100)
    trust_level: TrustLevel
    checks: list[Check]
    questions_to_ask_seller: list[str] = []


class SpeciesOption(BaseModel):
    species: str
    why: list[str]
    watch_outs: list[str] = []
    typical_price_range_inr: tuple[int, int] | None = None


class Phase(BaseModel):
    title: str
    steps: list[str]


class EnquiryReply(BaseModel):
    """A reply the seller can edit and send, drafted from the listing's facts only."""

    reply: str = Field(description="The message to the buyer, at most 90 words, in the buyer's language.")
    needs_seller_input: list[str] = Field(default=[], description=(
        "Questions the buyer asked that the listing facts don't answer, e.g. 'visit times'."))


class CarePlan(BaseModel):
    species: str
    phases: list[Phase]
    diet: list[str]
    daily_routine: list[str]
    see_vet_if: list[str] = Field(min_length=3)
    disclaimer: str = ""


# ---------------------------------------------------------------- October additions (docs/product/04)
class CertificateRead(BaseModel):
    """What Gemini read from a breeder registration certificate photo. Pass/fail is decided in code."""

    is_breeder_certificate: bool = Field(description=(
        "True only for a dog-breeding establishment registration certificate from a State Animal Welfare "
        "Board (or similar government animal-welfare authority)."))
    readable: bool
    registration_no: str | None = None
    holder_name: str | None = Field(default=None, description="The person or establishment it is issued to.")
    state: str | None = None
    address: str | None = None
    valid_until: str | None = Field(default=None, description="Expiry date as YYYY-MM-DD, if shown.")


class FacilityReview(BaseModel):
    """Gemini's observations of a breeder's facility photos. Pass/fail is decided in code."""

    shows_animal_housing: bool = Field(description="Cages, aviaries, kennels or rooms for animals.")
    space: Literal["adequate", "cramped", "unclear"]
    cleanliness: Literal["clean", "dirty", "unclear"]
    overcrowded: bool
    animal_condition: Literal["healthy_looking", "concerning", "no_animals_visible"]
    looks_like_stock_or_screenshot: bool
    observations: list[str] = Field(default=[], description="Short neutral phrases, e.g. 'fresh water'.")


class VaccineEntry(BaseModel):
    vaccine: str
    date: str | None = Field(default=None, description="YYYY-MM-DD if shown.")


class VaccinationRead(BaseModel):
    """What Gemini read from a pet's vaccination card or record."""

    is_vaccination_record: bool
    readable: bool
    species: str | None = None
    entries: list[VaccineEntry] = []
    clinic: str | None = None


class BuyerProfile(BaseModel):
    """A buyer's home and lifestyle, used to score species compatibility in code."""

    animal_group: Literal["bird", "dog", "cat", "any"] = "any"
    home_type: Literal["flat", "house"] = "flat"
    has_young_children: bool = False
    first_time_owner: bool = True
    time_per_day_minutes: int = Field(default=60, ge=0, le=600)
    hours_away_per_day: int = Field(default=8, ge=0, le=24)
    noise_ok: bool = True
    activity: Literal["low", "medium", "high"] = "medium"
    allergies: bool = False
    budget_inr: int | None = Field(default=None, gt=0)
    district: str | None = None


class OpeningMessage(BaseModel):
    message: str = Field(description="The buyer's first message to the breeder, at most 60 words.")


class MessageScan(BaseModel):
    """Gemini's read of a buyer–seller message for scam patterns; combined with fixed rules in code."""

    risk: Literal["none", "low", "high"]
    signals: list[str] = Field(default=[], description="Short phrases, e.g. 'asks for full advance payment'.")


class CareSuggestion(BaseModel):
    food_ok: bool = Field(description="False if a logged food is unsafe or unsuitable for the species.")
    feedback: str = Field(description="One or two kind sentences about today's log.")
    suggestions: list[str] = Field(default=[], description="Up to 3 practical tips for food or play.")


class SymptomCheck(BaseModel):
    urgency: Literal["emergency", "vet_soon", "monitor"]
    possible_meaning: str = Field(description="Plain words, never a diagnosis; no medicine names or doses.")
    watch_for: list[str] = []
    do_now: list[str] = Field(default=[], description="Safe first steps: warmth, quiet, water, a vet.")
