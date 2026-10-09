from fastapi import APIRouter

from breedernear_core.config import get_settings

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "model": settings.breedernear_model, "version": settings.git_sha}
