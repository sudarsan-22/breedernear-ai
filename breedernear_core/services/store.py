"""Persistence for drafts, listings and enquiries.

Firestore in the cloud, in-memory for tests and local runs.
"""

import copy
from typing import Protocol


class Store(Protocol):
    def save_draft(self, draft_id: str, data: dict) -> None: ...
    def get_draft(self, draft_id: str) -> dict | None: ...
    def delete_draft(self, draft_id: str) -> None: ...
    def save_listing(self, listing_id: str, data: dict) -> None: ...
    def get_listing(self, listing_id: str) -> dict | None: ...
    def all_listings(self) -> list[dict]: ...
    def save_enquiry(self, enquiry_id: str, data: dict) -> None: ...
    def all_enquiries(self) -> list[dict]: ...


class MemoryStore:
    def __init__(self) -> None:
        self.drafts: dict[str, dict] = {}
        self.listings: dict[str, dict] = {}
        self.enquiries: dict[str, dict] = {}

    def save_draft(self, draft_id: str, data: dict) -> None:
        self.drafts[draft_id] = copy.deepcopy(data)

    def get_draft(self, draft_id: str) -> dict | None:
        return copy.deepcopy(self.drafts.get(draft_id))

    def delete_draft(self, draft_id: str) -> None:
        self.drafts.pop(draft_id, None)

    def save_listing(self, listing_id: str, data: dict) -> None:
        self.listings[listing_id] = copy.deepcopy(data)

    def get_listing(self, listing_id: str) -> dict | None:
        return copy.deepcopy(self.listings.get(listing_id))

    def all_listings(self) -> list[dict]:
        return [copy.deepcopy(v) for v in self.listings.values()]

    def save_enquiry(self, enquiry_id: str, data: dict) -> None:
        self.enquiries[enquiry_id] = copy.deepcopy(data)

    def all_enquiries(self) -> list[dict]:
        return [copy.deepcopy(v) for v in self.enquiries.values()]


class FirestoreStore:
    def __init__(self, project: str | None = None) -> None:
        from google.cloud import firestore

        self._db = firestore.Client(project=project)

    def save_draft(self, draft_id: str, data: dict) -> None:
        self._db.collection("drafts").document(draft_id).set(data)

    def get_draft(self, draft_id: str) -> dict | None:
        snap = self._db.collection("drafts").document(draft_id).get()
        return snap.to_dict() if snap.exists else None

    def delete_draft(self, draft_id: str) -> None:
        self._db.collection("drafts").document(draft_id).delete()

    def save_listing(self, listing_id: str, data: dict) -> None:
        self._db.collection("listings").document(listing_id).set(data)

    def get_listing(self, listing_id: str) -> dict | None:
        snap = self._db.collection("listings").document(listing_id).get()
        return snap.to_dict() if snap.exists else None

    def all_listings(self) -> list[dict]:
        return [d.to_dict() for d in self._db.collection("listings").stream()]

    def save_enquiry(self, enquiry_id: str, data: dict) -> None:
        self._db.collection("enquiries").document(enquiry_id).set(data)

    def all_enquiries(self) -> list[dict]:
        return [d.to_dict() for d in self._db.collection("enquiries").stream()]
