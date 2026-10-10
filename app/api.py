from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from breedernear_core import care_service, deps, directory_service, match_service
from breedernear_core import listing_service as svc
from breedernear_core.config import get_settings
from breedernear_core.data import load_seed
from breedernear_core.services.uploads import ALLOWED_KINDS, ALLOWED_TYPES

router = APIRouter(prefix="/api")


def _guest(guest_id: str | None) -> str:
    if not guest_id or len(guest_id) > 64 or not guest_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Missing or invalid X-Guest-Id header.")
    return guest_id


def _call(fn, *args) -> dict:
    try:
        return fn(*args)
    except svc.ListingError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = 1


class TextAndPhotosIn(BaseModel):
    text: str = ""
    upload_ids: list[str] = []


class QuizIn(BaseModel):
    animal_group: str = "any"
    home_type: str = "flat"
    has_young_children: bool = False
    first_time_owner: bool = True
    time_per_day_minutes: int = 60
    noise_ok: bool = True
    budget_inr: int | None = None


class EnquiryIn(BaseModel):
    listing_id: str
    message: str


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "model": settings.breedernear_model, "version": settings.git_sha}


@router.post("/uploads")
async def upload(
    file: UploadFile = File(...),
    kind: str = Form("listing_photo"),
    x_guest_id: str | None = Header(default=None),
) -> dict:
    guest_id = _guest(x_guest_id)
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="Unknown upload kind.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Please upload a JPEG, PNG, WebP or HEIC photo.")
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        limit_mb = get_settings().max_upload_mb
        raise HTTPException(status_code=413, detail=f"Photos must be under {limit_mb} MB.")
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")
    upload_id = deps.get_uploads().put(guest_id, data, file.content_type, kind)
    return {"upload_id": upload_id}


@router.get("/breeder/listings")
def breeder_listings(x_guest_id: str | None = Header(default=None)) -> dict:
    return svc.my_listings(_guest(x_guest_id))


@router.get("/breeder/enquiries")
def breeder_enquiries(x_guest_id: str | None = Header(default=None)) -> dict:
    return match_service.my_enquiries(_guest(x_guest_id))


@router.get("/listings")
def listings(species: str, district: str, max_price: int | None = None,
             x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(match_service.search_listings, _guest(x_guest_id), species, district, max_price)


@router.get("/listings/{listing_id}")
def listing(listing_id: str, x_guest_id: str | None = Header(default=None)) -> dict:
    guest_id = _guest(x_guest_id)
    try:
        return match_service.get_listing(guest_id, listing_id)
    except svc.ListingError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/enquiries")
def enquiries(body: EnquiryIn, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(match_service.create_enquiry, _guest(x_guest_id), body.listing_id, body.message)


@router.get("/cart")
def cart(x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(care_service.view_cart, _guest(x_guest_id))


@router.post("/cart/items")
def cart_add(body: CartItemIn, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(care_service.add_to_cart, _guest(x_guest_id), [body.product_id], body.quantity)


@router.delete("/cart/items/{product_id}")
def cart_remove(product_id: str, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(care_service.remove_from_cart, _guest(x_guest_id), product_id)


# ---- Tabs: Pets, Local Breeders, My farm (same service functions as the agents' tools) ----

@router.get("/meta")
def meta() -> dict:
    districts = [{"key": d["key"], "name": d["name"]} for d in load_seed("districts.json")["districts"]]
    return {"districts": districts, "default_district": "coimbatore"}


@router.get("/pets")
def pets(district: str | None = None, species: str | None = None, max_price: int | None = None,
         trusted_only: bool = False, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(match_service.browse_pets, _guest(x_guest_id), district, species, max_price, trusted_only)


@router.post("/recommend")
def recommend(body: QuizIn) -> dict:
    return _call(match_service.recommend_species, body.animal_group, body.home_type, body.has_young_children,
                 body.first_time_owner, body.time_per_day_minutes, body.noise_ok, body.budget_inr)


@router.get("/breeders")
def breeders_list(district: str | None = None, species: str | None = None,
                  x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(directory_service.list_breeders, _guest(x_guest_id), district, species)


@router.get("/breeders/{breeder_id}")
def breeder_page(breeder_id: str, district: str | None = None,
                 x_guest_id: str | None = Header(default=None)) -> dict:
    guest_id = _guest(x_guest_id)
    try:
        return directory_service.get_breeder(guest_id, breeder_id, district)
    except svc.ListingError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/sell/drafts")
def sell_draft(body: TextAndPhotosIn, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(svc.extract_listing, _guest(x_guest_id), body.text, body.upload_ids)


@router.patch("/sell/drafts/{draft_id}")
def sell_edit(draft_id: str, body: dict, x_guest_id: str | None = Header(default=None)) -> dict:
    guest_id = _guest(x_guest_id)
    if not body:
        raise HTTPException(status_code=400, detail="Nothing to change.")
    result: dict = {}
    for field, value in body.items():
        result = _call(svc.update_draft, guest_id, draft_id, field, "" if value is None else str(value))
    return result


@router.post("/sell/drafts/{draft_id}/publish")
def sell_publish(draft_id: str, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(svc.publish_listing, _guest(x_guest_id), draft_id)


@router.post("/check")
def check_post(body: TextAndPhotosIn, x_guest_id: str | None = Header(default=None)) -> dict:
    return _call(svc.check_external_listing, _guest(x_guest_id), body.text, body.upload_ids)


@router.get("/starter-kit")
def starter_kit(species: str, count: int = 2) -> dict:
    return _call(care_service.build_starter_kit, species, count)


@router.get("/care-plan")
def care_plan(species: str, age_months: int | None = None) -> dict:
    return _call(care_service.care_plan, species, age_months)
