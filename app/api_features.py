"""REST routes for the October features (docs/product/04-feature-spec-oct.md).

Same rules as app/api.py: every route needs a signed-in account, roles are checked here and in the services,
and the routes call the same service functions as the agents' tools.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api import _call, seller
from breedernear_core import analytics_service, verification_service

router = APIRouter(prefix="/api")


class PhoneIn(BaseModel):
    phone: str
    code: str | None = None


class UploadsIn(BaseModel):
    upload_ids: list[str]


class UploadIn(BaseModel):
    upload_id: str


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
