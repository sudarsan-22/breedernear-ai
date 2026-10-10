"""Chooses real Google Cloud services or in-memory fakes. Tests replace them with set_deps()."""

from breedernear_core.catalog import seed_listings
from breedernear_core.config import get_settings
from breedernear_core.services.store import FirestoreStore, MemoryStore, Store
from breedernear_core.services.uploads import GcsUploads, MemoryUploads, UploadStore
from breedernear_core.services.vision import GeminiVision, Vision

_store: Store | None = None
_uploads: UploadStore | None = None
_vision: Vision | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        if get_settings().breedernear_backend == "gcp":
            _store = FirestoreStore()    # seeded once with scripts/seed_firestore.py
        else:
            _store = MemoryStore()
            for listing in seed_listings():
                _store.save_listing(listing["id"], listing)
    return _store


def get_uploads() -> UploadStore:
    global _uploads
    if _uploads is None:
        s = get_settings()
        _uploads = GcsUploads(s.breedernear_bucket) if s.breedernear_backend == "gcp" else MemoryUploads()
    return _uploads


def get_vision() -> Vision:
    global _vision
    if _vision is None:
        _vision = GeminiVision(get_settings().breedernear_model)
    return _vision


def set_deps(store: Store | None = None, uploads: UploadStore | None = None,
             vision: Vision | None = None) -> None:
    global _store, _uploads, _vision
    _store, _uploads, _vision = store, uploads, vision
