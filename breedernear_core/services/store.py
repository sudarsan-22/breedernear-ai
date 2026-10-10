"""Persistence for accounts, sessions, drafts, listings, enquiries and demo carts.

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
    def get_enquiry(self, enquiry_id: str) -> dict | None: ...
    def all_enquiries(self) -> list[dict]: ...
    def save_cart(self, guest_id: str, data: dict) -> None: ...
    def get_cart(self, guest_id: str) -> dict | None: ...
    def delete_listing(self, listing_id: str) -> None: ...
    def delete_enquiry(self, enquiry_id: str) -> None: ...
    def save_user(self, user_id: str, data: dict) -> None: ...
    def get_user(self, user_id: str) -> dict | None: ...
    def delete_user(self, user_id: str) -> None: ...
    def claim_login(self, login: str, user_id: str) -> bool: ...
    def login_owner(self, login: str) -> str | None: ...
    def release_login(self, login: str) -> None: ...
    def save_session(self, key: str, data: dict) -> None: ...
    def get_session(self, key: str) -> dict | None: ...
    def delete_session(self, key: str) -> None: ...
    def delete_sessions_of(self, user_id: str) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self.drafts: dict[str, dict] = {}
        self.listings: dict[str, dict] = {}
        self.enquiries: dict[str, dict] = {}
        self.carts: dict[str, dict] = {}
        self.users: dict[str, dict] = {}
        self.logins: dict[str, str] = {}
        self.sessions: dict[str, dict] = {}

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

    def get_enquiry(self, enquiry_id: str) -> dict | None:
        return copy.deepcopy(self.enquiries.get(enquiry_id))

    def all_enquiries(self) -> list[dict]:
        return [copy.deepcopy(v) for v in self.enquiries.values()]

    def save_cart(self, guest_id: str, data: dict) -> None:
        self.carts[guest_id] = copy.deepcopy(data)

    def get_cart(self, guest_id: str) -> dict | None:
        return copy.deepcopy(self.carts.get(guest_id))

    def delete_listing(self, listing_id: str) -> None:
        self.listings.pop(listing_id, None)

    def delete_enquiry(self, enquiry_id: str) -> None:
        self.enquiries.pop(enquiry_id, None)

    def save_user(self, user_id: str, data: dict) -> None:
        self.users[user_id] = copy.deepcopy(data)

    def get_user(self, user_id: str) -> dict | None:
        return copy.deepcopy(self.users.get(user_id))

    def delete_user(self, user_id: str) -> None:
        self.users.pop(user_id, None)

    def claim_login(self, login: str, user_id: str) -> bool:
        if login in self.logins:
            return False
        self.logins[login] = user_id
        return True

    def login_owner(self, login: str) -> str | None:
        return self.logins.get(login)

    def release_login(self, login: str) -> None:
        self.logins.pop(login, None)

    def save_session(self, key: str, data: dict) -> None:
        self.sessions[key] = copy.deepcopy(data)

    def get_session(self, key: str) -> dict | None:
        return copy.deepcopy(self.sessions.get(key))

    def delete_session(self, key: str) -> None:
        self.sessions.pop(key, None)

    def delete_sessions_of(self, user_id: str) -> None:
        for key in [k for k, v in self.sessions.items() if v["user_id"] == user_id]:
            del self.sessions[key]


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

    def get_enquiry(self, enquiry_id: str) -> dict | None:
        snap = self._db.collection("enquiries").document(enquiry_id).get()
        return snap.to_dict() if snap.exists else None

    def all_enquiries(self) -> list[dict]:
        return [d.to_dict() for d in self._db.collection("enquiries").stream()]

    def save_cart(self, guest_id: str, data: dict) -> None:
        self._db.collection("carts").document(guest_id).set(data)

    def get_cart(self, guest_id: str) -> dict | None:
        snap = self._db.collection("carts").document(guest_id).get()
        return snap.to_dict() if snap.exists else None

    def delete_listing(self, listing_id: str) -> None:
        self._db.collection("listings").document(listing_id).delete()

    def delete_enquiry(self, enquiry_id: str) -> None:
        self._db.collection("enquiries").document(enquiry_id).delete()

    def save_user(self, user_id: str, data: dict) -> None:
        self._db.collection("users").document(user_id).set(data)

    def get_user(self, user_id: str) -> dict | None:
        snap = self._db.collection("users").document(user_id).get()
        return snap.to_dict() if snap.exists else None

    def delete_user(self, user_id: str) -> None:
        self._db.collection("users").document(user_id).delete()

    def claim_login(self, login: str, user_id: str) -> bool:
        from google.api_core.exceptions import AlreadyExists, Conflict

        try:
            self._db.collection("login_index").document(login).create({"user_id": user_id})
            return True
        except (AlreadyExists, Conflict):
            return False

    def login_owner(self, login: str) -> str | None:
        snap = self._db.collection("login_index").document(login).get()
        return snap.to_dict()["user_id"] if snap.exists else None

    def release_login(self, login: str) -> None:
        self._db.collection("login_index").document(login).delete()

    def save_session(self, key: str, data: dict) -> None:
        self._db.collection("auth_sessions").document(key).set(data)

    def get_session(self, key: str) -> dict | None:
        snap = self._db.collection("auth_sessions").document(key).get()
        return snap.to_dict() if snap.exists else None

    def delete_session(self, key: str) -> None:
        self._db.collection("auth_sessions").document(key).delete()

    def delete_sessions_of(self, user_id: str) -> None:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self._db.collection("auth_sessions").where(filter=FieldFilter("user_id", "==", user_id))
        for snap in query.stream():
            snap.reference.delete()
