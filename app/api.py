"""BreederNear REST API. Every route except health, meta and auth needs a signed-in user (Bearer token).

The routes call the same service functions as the agents' tools; roles are checked here and in the tools.
"""

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from breedernear_core import accounts, care_service, deps, directory_service, match_service
from breedernear_core import listing_service as svc
from breedernear_core.config import get_settings
from breedernear_core.data import load_seed
from breedernear_core.match_service import Viewer
from breedernear_core.services.uploads import ALLOWED_KINDS, ALLOWED_TYPES

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------- auth helpers
def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _account_error(e: accounts.AccountError) -> HTTPException:
    return HTTPException(status_code=e.status, detail=str(e))


def current_user(authorization: str | None = Header(default=None)) -> dict:
    try:
        return accounts.authenticate(bearer(authorization))
    except accounts.AccountError as e:
        raise _account_error(e) from e


def seller(user: dict = Depends(current_user)) -> dict:
    try:
        accounts.require_role(user, "seller")
    except accounts.AccountError as e:
        raise _account_error(e) from e
    return user


def customer(user: dict = Depends(current_user)) -> dict:
    try:
        accounts.require_role(user, "customer")
    except accounts.AccountError as e:
        raise _account_error(e) from e
    return user


def viewer(user: dict) -> Viewer:
    return Viewer(user["id"], user.get("session_device_id"))


def _call(fn, *args, not_found: bool = False) -> dict:
    try:
        return fn(*args)
    except svc.ListingError as e:
        raise HTTPException(status_code=404 if not_found else 400, detail=str(e)) from e
    except accounts.AccountError as e:
        raise _account_error(e) from e


# ---------------------------------------------------------------- bodies
class SignupIn(BaseModel):
    role: str
    name: str
    login: str
    password: str
    district: str | None = None
    remember: bool = True
    farm: dict | None = None


class LoginIn(BaseModel):
    login: str
    password: str
    remember: bool = True


class DemoIn(BaseModel):
    role: str


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


class StatusIn(BaseModel):
    status: str


# ---------------------------------------------------------------- public
@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "model": settings.breedernear_model, "version": settings.git_sha}


@router.get("/meta")
def meta() -> dict:
    districts = [{"key": d["key"], "name": d["name"]} for d in load_seed("districts.json")["districts"]]
    return {"districts": districts, "default_district": "coimbatore"}


# ---------------------------------------------------------------- accounts
def _session(token: str, user: dict) -> dict:
    return {"token": token, "user": user}


@router.post("/auth/signup")
def signup(body: SignupIn, x_device_id: str | None = Header(default=None)) -> dict:
    return _session(*_call(accounts.signup, body.role, body.name, body.login, body.password, body.district,
                           x_device_id, body.remember, body.farm))


@router.post("/auth/login")
def login(body: LoginIn, x_device_id: str | None = Header(default=None)) -> dict:
    return _session(*_call(accounts.login, body.login, body.password, x_device_id, body.remember))


@router.post("/auth/demo")
def demo(body: DemoIn, x_device_id: str | None = Header(default=None)) -> dict:
    return _session(*_call(accounts.demo, body.role, x_device_id))


@router.get("/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    return {"user": user}


@router.patch("/auth/me")
def update_me(body: dict, user: dict = Depends(current_user)) -> dict:
    return {"user": _call(accounts.update_profile, user, body)}


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    accounts.logout(bearer(authorization))
    return {"status": "ok"}


@router.delete("/auth/me")
def delete_me(user: dict = Depends(current_user)) -> dict:
    accounts.delete_account(user)
    return {"status": "ok"}


# ---------------------------------------------------------------- shared (any signed-in user)
@router.post("/uploads")
async def upload(file: UploadFile = File(...), kind: str = Form("listing_photo"),
                 user: dict = Depends(current_user)) -> dict:
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="Unknown upload kind.")
    if kind == "listing_photo" and user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Only seller accounts can upload listing photos.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Please upload a JPEG, PNG, WebP or HEIC photo.")
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        limit_mb = get_settings().max_upload_mb
        raise HTTPException(status_code=413, detail=f"Photos must be under {limit_mb} MB.")
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")
    return {"upload_id": deps.get_uploads().put(user["id"], data, file.content_type, kind)}


@router.get("/pets")
def pets(district: str | None = None, species: str | None = None, max_price: int | None = None,
         trusted_only: bool = False, user: dict = Depends(current_user)) -> dict:
    return _call(match_service.browse_pets, viewer(user), district, species, max_price, trusted_only)


@router.get("/listings")
def listings(species: str, district: str, max_price: int | None = None,
             user: dict = Depends(current_user)) -> dict:
    return _call(match_service.search_listings, viewer(user), species, district, max_price)


@router.get("/listings/{listing_id}")
def listing(listing_id: str, user: dict = Depends(current_user)) -> dict:
    return _call(match_service.get_listing, viewer(user), listing_id, not_found=True)


@router.post("/recommend")
def recommend(body: QuizIn, user: dict = Depends(current_user)) -> dict:
    return _call(match_service.recommend_species, body.animal_group, body.home_type, body.has_young_children,
                 body.first_time_owner, body.time_per_day_minutes, body.noise_ok, body.budget_inr)


@router.get("/breeders")
def breeders_list(district: str | None = None, species: str | None = None,
                  user: dict = Depends(current_user)) -> dict:
    return _call(directory_service.list_breeders, viewer(user), district, species)


@router.get("/breeders/{breeder_id}")
def breeder_page(breeder_id: str, district: str | None = None, user: dict = Depends(current_user)) -> dict:
    return _call(directory_service.get_breeder, viewer(user), breeder_id, district, not_found=True)


@router.post("/check")
def check_post(body: TextAndPhotosIn, user: dict = Depends(current_user)) -> dict:
    return _call(svc.check_external_listing, user["id"], body.text, body.upload_ids)


@router.get("/starter-kit")
def starter_kit(species: str, count: int = 2, user: dict = Depends(current_user)) -> dict:
    return _call(care_service.build_starter_kit, species, count)


@router.get("/care-plan")
def care_plan(species: str, age_months: int | None = None, user: dict = Depends(current_user)) -> dict:
    return _call(care_service.care_plan, species, age_months)


# ---------------------------------------------------------------- customers only
@router.post("/enquiries")
def enquiries(body: EnquiryIn, user: dict = Depends(customer)) -> dict:
    return _call(match_service.create_enquiry, viewer(user), body.listing_id, body.message)


@router.get("/enquiries/sent")
def enquiries_sent(user: dict = Depends(customer)) -> dict:
    return match_service.sent_enquiries(viewer(user))


@router.get("/cart")
def cart(user: dict = Depends(customer)) -> dict:
    return _call(care_service.view_cart, user["id"])


@router.post("/cart/items")
def cart_add(body: CartItemIn, user: dict = Depends(customer)) -> dict:
    return _call(care_service.add_to_cart, user["id"], [body.product_id], body.quantity)


@router.delete("/cart/items/{product_id}")
def cart_remove(product_id: str, user: dict = Depends(customer)) -> dict:
    return _call(care_service.remove_from_cart, user["id"], product_id)


# ---------------------------------------------------------------- sellers only
@router.get("/seller/dashboard")
def seller_dashboard(user: dict = Depends(seller)) -> dict:
    return svc.seller_dashboard(user["id"]) | {"farm": user.get("farm")}


@router.get("/seller/listings")
def seller_listings(user: dict = Depends(seller)) -> dict:
    return svc.my_listings(user["id"])


@router.patch("/seller/listings/{listing_id}")
def seller_listing_status(listing_id: str, body: StatusIn, user: dict = Depends(seller)) -> dict:
    return _call(svc.set_listing_status, user["id"], listing_id, body.status)


@router.delete("/seller/listings/{listing_id}")
def seller_listing_delete(listing_id: str, user: dict = Depends(seller)) -> dict:
    return _call(svc.delete_listing, user["id"], listing_id)


@router.get("/seller/enquiries")
def seller_enquiries(user: dict = Depends(seller)) -> dict:
    return match_service.my_enquiries(user["id"])


@router.post("/sell/drafts")
def sell_draft(body: TextAndPhotosIn, user: dict = Depends(seller)) -> dict:
    return _call(svc.extract_listing, user["id"], body.text, body.upload_ids)


@router.patch("/sell/drafts/{draft_id}")
def sell_edit(draft_id: str, body: dict, user: dict = Depends(seller)) -> dict:
    if not body:
        raise HTTPException(status_code=400, detail="Nothing to change.")
    result: dict = {}
    for field, value in body.items():
        result = _call(svc.update_draft, user["id"], draft_id, field, "" if value is None else str(value))
    return result


@router.post("/sell/drafts/{draft_id}/publish")
def sell_publish(draft_id: str, user: dict = Depends(seller)) -> dict:
    return _call(svc.publish_listing, user["id"], draft_id, user.get("session_device_id"))
