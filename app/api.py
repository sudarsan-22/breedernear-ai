from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from breedernear_core import deps
from breedernear_core import listing_service as svc
from breedernear_core.config import get_settings
from breedernear_core.services.uploads import ALLOWED_KINDS, ALLOWED_TYPES

router = APIRouter(prefix="/api")


def _guest(guest_id: str | None) -> str:
    if not guest_id or len(guest_id) > 64 or not guest_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Missing or invalid X-Guest-Id header.")
    return guest_id


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
