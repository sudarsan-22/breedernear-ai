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


class CarePlan(BaseModel):
    species: str
    phases: list[Phase]
    diet: list[str]
    daily_routine: list[str]
    see_vet_if: list[str] = Field(min_length=3)
    disclaimer: str = ""
