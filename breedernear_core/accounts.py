"""Customer and seller accounts: sign-up, login, demo accounts and sessions.

One account has one role. Passwords are stored only as salted scrypt hashes; login tokens are random
and stored only as SHA-256 hashes. Docs: docs/product/02-requirements.md (Accounts section).
"""

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from breedernear_core import deps
from breedernear_core.services.geo import resolve_district
from breedernear_core.services.registry import sawb_status

ROLES = ("customer", "seller")
SELLER_TYPES = ("home_breeder", "kennel", "farm")
MIN_PASSWORD = 8
REMEMBER_DAYS, SESSION_HOURS = 30, 24
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,}$")
DEMO = {
    "customer": {"name": "Priya (demo)", "district": "tiruppur"},
    "seller": {"name": "Karthik (demo)", "district": "coimbatore",
               "farm": {"farm_name": "Karthik's Demo Aviary", "seller_type": "home_breeder",
                        "locality": "Saibaba Colony", "species": ["lovebird", "budgerigar", "cockatiel"],
                        "sawb_registration_no": None}},
}


class AccountError(Exception):
    """A problem to show the user. status follows HTTP (400 bad input, 401 login, 403 role, 409 taken)."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_login(raw: str) -> tuple[str, str]:
    """Return (login, kind): lower-case email, or an Indian mobile as +91XXXXXXXXXX."""
    value = (raw or "").strip()
    if "@" in value:
        email = value.lower()
        if not EMAIL.match(email):
            raise AccountError("Please enter a valid email address.")
        return email, "email"
    digits = re.sub(r"[\s\-()]", "", value)
    digits = re.sub(r"^(\+91|0091|91(?=\d{10}$)|0(?=\d{10}$))", "", digits)
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise AccountError("Please enter a valid email address or a 10-digit Indian mobile number.")
    return f"+91{digits}", "mobile"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        _, n, r, p, salt, digest = (stored or "").split("$")
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _verification(farm: dict, has_dogs: bool) -> str:
    """'verified' | 'expired' | 'not_found' | 'missing' (dog breeders) | 'not_required'."""
    number = (farm.get("sawb_registration_no") or "").strip()
    if number:
        return {"valid": "verified", "expired": "expired"}.get(sawb_status(number), "not_found")
    return "missing" if has_dogs else "not_required"


def _clean_farm(farm: dict | None) -> dict:
    farm = farm or {}
    name = (farm.get("farm_name") or "").strip()[:80]
    if len(name) < 2:
        raise AccountError("Please enter your farm or kennel name.")
    seller_type = farm.get("seller_type") or "home_breeder"
    if seller_type not in SELLER_TYPES:
        raise AccountError("Please choose home breeder, kennel or farm.")
    species = [str(s)[:40] for s in (farm.get("species") or [])][:10]
    clean = {"farm_name": name, "seller_type": seller_type,
             "locality": (farm.get("locality") or "").strip()[:80], "species": species,
             "sawb_registration_no": (farm.get("sawb_registration_no") or "").strip()[:40] or None}
    has_dogs = any(s.lower() in ("dog", "dogs", "labrador", "beagle", "shih_tzu") for s in species)
    clean["verification"] = _verification(clean, has_dogs)
    return clean


def public(user: dict) -> dict:
    out = {k: v for k, v in user.items() if k not in ("password_hash",)}
    return out


def _start_session(user: dict, device_id: str, remember: bool) -> str:
    token = secrets.token_urlsafe(32)
    expires = _now() + (timedelta(days=REMEMBER_DAYS) if remember else timedelta(hours=SESSION_HOURS))
    session = {"user_id": user["id"], "role": user["role"], "device_id": device_id,
               "expires_at": expires.isoformat()}
    deps.get_store().save_session(_token_key(token), session)
    return token


def _device(device_id: str | None) -> str:
    if not device_id or len(device_id) > 64 or not device_id.replace("-", "").isalnum():
        raise AccountError("Missing device ID. Please reload the page.")
    return device_id


def signup(role: str, name: str, login: str, password: str, district: str | None, device_id: str | None,
           remember: bool = True, farm: dict | None = None) -> tuple[str, dict]:
    if role not in ROLES:
        raise AccountError("Choose whether you want to buy or sell pets.")
    name = (name or "").strip()[:60]
    if len(name) < 2:
        raise AccountError("Please enter your name.")
    login_value, kind = normalize_login(login)
    if len(password or "") < MIN_PASSWORD:
        raise AccountError(f"Use a password of at least {MIN_PASSWORD} characters.")
    district_key = resolve_district(district) if district else None
    if district and not district_key:
        raise AccountError("Please choose your district from the list.")
    device = _device(device_id)
    user_id = f"USR_{uuid.uuid4().hex[:16]}"
    store = deps.get_store()
    if not store.claim_login(login_value, user_id):
        raise AccountError(f"An account with this {kind} already exists. Please log in.", 409)
    user = {"id": user_id, "role": role, "name": name, "login": login_value, "login_type": kind,
            "password_hash": hash_password(password), "district": district_key, "device_id": device,
            "demo": False, "created_at": _now().isoformat()}
    if role == "seller":
        try:
            user["farm"] = _clean_farm(farm)
        except AccountError:
            store.release_login(login_value)
            raise
    store.save_user(user_id, user)
    return _start_session(user, device, remember), public(user)


def login(login_value: str, password: str, device_id: str | None, remember: bool = True) -> tuple[str, dict]:
    wrong = AccountError("Wrong email/mobile or password.", 401)
    try:
        normalized, _ = normalize_login(login_value)
    except AccountError as e:
        raise wrong from e
    store = deps.get_store()
    user_id = store.login_owner(normalized)
    user = store.get_user(user_id) if user_id else None
    if not verify_password(password or "", user["password_hash"] if user else None):
        if user is None:
            verify_password(password or "", hash_password("timing-equaliser"))
        raise wrong
    return _start_session(user, _device(device_id), remember), public(user)


def demo(role: str, device_id: str | None) -> tuple[str, dict]:
    if role not in ROLES:
        raise AccountError("Unknown demo account.")
    preset = DEMO[role]
    user_id = f"DEMO_{uuid.uuid4().hex[:16]}"
    user = {"id": user_id, "role": role, "name": preset["name"], "login": None, "login_type": None,
            "password_hash": None, "district": preset["district"], "device_id": _device(device_id),
            "demo": True, "created_at": _now().isoformat()}
    if role == "seller":
        user["farm"] = _clean_farm(preset["farm"])
    deps.get_store().save_user(user_id, user)
    return _start_session(user, user["device_id"], remember=False), public(user)


def authenticate(token: str | None) -> dict:
    """Return the signed-in user with the session's device ID, or raise 401."""
    if not token:
        raise AccountError("Please log in.", 401)
    store = deps.get_store()
    session = store.get_session(_token_key(token))
    if not session or datetime.fromisoformat(session["expires_at"]) < _now():
        raise AccountError("Your session has ended. Please log in again.", 401)
    user = store.get_user(session["user_id"])
    if not user:
        raise AccountError("Please log in.", 401)
    return public(user) | {"session_device_id": session["device_id"]}


def get_user(user_id: str) -> dict | None:
    user = deps.get_store().get_user(user_id)
    return public(user) if user else None


def require_role(user: dict | None, role: str) -> None:
    if not user:
        raise AccountError("Please log in.", 401)
    if user["role"] != role:
        if role == "seller":
            raise AccountError("Selling uses a separate seller account. Sign up and choose “Sell pets”.", 403)
        raise AccountError("This is for customers. Your seller account can't buy or use the cart.", 403)


def logout(token: str | None) -> None:
    if token:
        deps.get_store().delete_session(_token_key(token))


def update_profile(user: dict, fields: dict) -> dict:
    store = deps.get_store()
    stored = store.get_user(user["id"])
    if "name" in fields:
        name = str(fields["name"]).strip()[:60]
        if len(name) < 2:
            raise AccountError("Please enter your name.")
        stored["name"] = name
    if "district" in fields:
        key = resolve_district(str(fields["district"]))
        if not key:
            raise AccountError("Please choose your district from the list.")
        stored["district"] = key
    if "farm" in fields:
        require_role(stored, "seller")
        stored["farm"] = _clean_farm({**stored.get("farm", {}), **(fields["farm"] or {})})
    store.save_user(stored["id"], stored)
    return public(stored)


def delete_account(user: dict) -> None:
    """Remove the account, its sessions and its own listings (privacy: 'Delete my account')."""
    store = deps.get_store()
    for listing in store.all_listings():
        if listing.get("owner_user_id") == user["id"]:
            store.delete_listing(listing["id"])
    store.delete_sessions_of(user["id"])
    if user.get("login"):
        store.release_login(user["login"])
    store.delete_user(user["id"])
