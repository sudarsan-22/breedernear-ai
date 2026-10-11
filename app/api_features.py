"""REST routes for the October features (docs/product/04-feature-spec-oct.md).

Same rules as app/api.py: every route needs a signed-in account, roles are checked here and in the services,
and the routes call the same service functions as the agents' tools.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api import _call, customer, seller, viewer
from breedernear_core import (
    analytics_service,
    buyer_service,
    companion_service,
    journey_service,
    verification_service,
)

router = APIRouter(prefix="/api")


class PhoneIn(BaseModel):
    phone: str
    code: str | None = None


class UploadsIn(BaseModel):
    upload_ids: list[str]


class UploadIn(BaseModel):
    upload_id: str


class ProfileIn(BaseModel):
    words: str | None = None
    profile: dict | None = None


class VisitIn(BaseModel):
    listing_id: str
    date: str
    slot: str
    note: str = ""


class AnswerIn(BaseModel):
    action: str
    note: str = ""


class PurchaseIn(BaseModel):
    visit_id: str
    pet_name: str = ""


class LogIn(BaseModel):
    food: str = ""
    play: str = ""
    note: str = ""
    photo_upload_id: str | None = None


class WeightIn(BaseModel):
    value: float


class SymptomIn(BaseModel):
    text: str


# ---------------------------------------------------------------- seller: analytics and verification
@router.get("/seller/analytics")
def seller_analytics(user: dict = Depends(seller)) -> dict:
    return analytics_service.summary(user["id"])


@router.get("/seller/verification")
def verification(user: dict = Depends(seller)) -> dict:
    return _call(verification_service.status_of, user["id"])


@router.post("/seller/verification/phone/request")
def verification_phone_request(body: PhoneIn, user: dict = Depends(seller)) -> dict:
    return _call(verification_service.request_phone_code, user["id"], body.phone)


@router.post("/seller/verification/phone/verify")
def verification_phone_verify(body: PhoneIn, user: dict = Depends(seller)) -> dict:
    return _call(verification_service.confirm_phone, user["id"], body.phone, body.code or "")


@router.post("/seller/verification/facility")
def verification_facility(body: UploadsIn, user: dict = Depends(seller)) -> dict:
    return _call(verification_service.review_facility, user["id"], body.upload_ids)


@router.post("/seller/verification/certificate")
def verification_certificate(body: UploadIn, user: dict = Depends(seller)) -> dict:
    return _call(verification_service.review_certificate, user["id"], body.upload_id)


@router.get("/seller/visits")
def seller_visits(user: dict = Depends(seller)) -> dict:
    return journey_service.seller_visits(user["id"])


@router.post("/seller/visits/{visit_id}")
def seller_answer_visit(visit_id: str, body: AnswerIn, user: dict = Depends(seller)) -> dict:
    return _call(journey_service.answer_visit, user["id"], visit_id, body.action, body.note)


# ---------------------------------------------------------------- buyer: profile and first message
@router.get("/buyer/profile")
def buyer_profile(user: dict = Depends(customer)) -> dict:
    return buyer_service.get_profile(user["id"])


@router.post("/buyer/profile")
def buyer_profile_save(body: ProfileIn, user: dict = Depends(customer)) -> dict:
    return _call(buyer_service.save_profile, user["id"], body.profile, body.words)


@router.get("/buyer/compatibility")
def buyer_compatibility(user: dict = Depends(customer)) -> dict:
    return buyer_service.compatibility(user["id"])


@router.post("/listings/{listing_id}/opening-message")
def opening_message(listing_id: str, user: dict = Depends(customer)) -> dict:
    return _call(buyer_service.opening_message, viewer(user), listing_id, not_found=True)


# ---------------------------------------------------------------- buyer: visits and purchase
@router.get("/visits")
def my_visits(user: dict = Depends(customer)) -> dict:
    return journey_service.buyer_visits(viewer(user))


@router.post("/visits")
def book_visit(body: VisitIn, user: dict = Depends(customer)) -> dict:
    return _call(journey_service.request_visit, viewer(user), body.listing_id, body.date, body.slot,
                 body.note)


@router.post("/purchases")
def mark_bought(body: PurchaseIn, user: dict = Depends(customer)) -> dict:
    return _call(journey_service.purchase, viewer(user), body.visit_id, body.pet_name)


# ---------------------------------------------------------------- buyer: care companion
@router.get("/companion/pets")
def my_pets(user: dict = Depends(customer)) -> dict:
    return companion_service.list_pets(user["id"])


@router.get("/companion/pets/{pet_id}")
def my_pet(pet_id: str, user: dict = Depends(customer)) -> dict:
    return _call(companion_service.get_pet, user["id"], pet_id, not_found=True)


@router.post("/companion/pets/{pet_id}/log")
def pet_log(pet_id: str, body: LogIn, user: dict = Depends(customer)) -> dict:
    return _call(companion_service.log_day, user["id"], pet_id, body.food, body.play, body.note,
                 body.photo_upload_id)


@router.post("/companion/pets/{pet_id}/weight")
def pet_weight(pet_id: str, body: WeightIn, user: dict = Depends(customer)) -> dict:
    return _call(companion_service.add_weight, user["id"], pet_id, body.value)


@router.post("/companion/pets/{pet_id}/symptoms")
def pet_symptoms(pet_id: str, body: SymptomIn, user: dict = Depends(customer)) -> dict:
    return _call(companion_service.check_symptoms, user["id"], pet_id, body.text)
