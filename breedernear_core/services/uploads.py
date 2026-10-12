"""Uploaded images and voice notes: a private Cloud Storage bucket in the cloud, in memory for tests."""

import uuid
from typing import Protocol

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/aac", "audio/wav", "audio/x-wav"}
ALLOWED_KINDS = {"listing_photo", "external_listing", "vaccination", "certificate", "facility_photo",
                 "pet_photo", "food_photo", "voice_note"}
SELLER_KINDS = {"listing_photo", "vaccination", "certificate", "facility_photo", "voice_note"}
CUSTOMER_KINDS = {"pet_photo", "food_photo"}


class UploadStore(Protocol):
    def put(self, guest_id: str, data: bytes, content_type: str, kind: str) -> str: ...
    def get(self, guest_id: str, upload_id: str) -> tuple[bytes, str] | None: ...
    def delete(self, guest_id: str, upload_id: str) -> None: ...


def new_upload_id() -> str:
    return f"UPL_{uuid.uuid4().hex[:12]}"


class MemoryUploads:
    def __init__(self) -> None:
        self._files: dict[tuple[str, str], tuple[bytes, str]] = {}

    def put(self, guest_id: str, data: bytes, content_type: str, kind: str) -> str:
        upload_id = new_upload_id()
        self._files[(guest_id, upload_id)] = (data, content_type)
        return upload_id

    def get(self, guest_id: str, upload_id: str) -> tuple[bytes, str] | None:
        return self._files.get((guest_id, upload_id))

    def delete(self, guest_id: str, upload_id: str) -> None:
        self._files.pop((guest_id, upload_id), None)


class GcsUploads:
    """Objects live at uploads/{guest_id}/{upload_id}; a guest can only read their own uploads."""

    def __init__(self, bucket: str, project: str | None = None) -> None:
        from google.cloud import storage

        self._bucket = storage.Client(project=project).bucket(bucket)

    def put(self, guest_id: str, data: bytes, content_type: str, kind: str) -> str:
        upload_id = new_upload_id()
        blob = self._bucket.blob(f"uploads/{guest_id}/{upload_id}")
        blob.metadata = {"kind": kind}
        blob.upload_from_string(data, content_type=content_type)
        return upload_id

    def get(self, guest_id: str, upload_id: str) -> tuple[bytes, str] | None:
        blob = self._bucket.blob(f"uploads/{guest_id}/{upload_id}")
        if not blob.exists():
            return None
        blob.reload()
        return blob.download_as_bytes(), blob.content_type or "image/jpeg"

    def delete(self, guest_id: str, upload_id: str) -> None:
        blob = self._bucket.blob(f"uploads/{guest_id}/{upload_id}")
        if blob.exists():
            blob.delete()
