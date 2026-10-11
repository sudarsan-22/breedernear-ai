"""Breeder verification (F15): four layers, each pass / fail / pending with a plain-language reason.

1. Phone: confirmed with a one-time code.
2. Facility photos: 1–5 photos; Gemini describes space, cleanliness, crowding and the animals' condition.
3. Breeder registration certificate (dog breeders only): Gemini reads the certificate; code checks it against
   the SIMULATED State Animal Welfare Board registry, the expiry date, and that it is issued to this seller.
4. Overall status: verified when every required layer passes, rejected when any fails, otherwise pending.

No ID documents or selfies are collected (owner decision, 11 Oct). Gemini only reads and observes; every
pass/fail rule is here in code. Uploaded photos and certificates are deleted once read; only the result
is kept.
"""

from datetime import UTC, date, datetime

from breedernear_core import deps, otp_service
from breedernear_core.data import normalize
from breedernear_core.listing_service import ListingError
from breedernear_core.services.registry import registry_entry

COLLECTION = "verifications"
DOG_WORDS = {"dog", "dogs", "labrador", "beagle", "shih_tzu", "shih tzu", "puppy", "puppies"}
MAX_FACILITY_PHOTOS = 5
LAYERS = ("phone", "facility", "certificate")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _user(user_id: str) -> dict:
    user = deps.get_store().get_user(user_id)
    if user is None or user.get("role") != "seller":
        raise ListingError("Only seller accounts can be verified.")
    return user


def breeds_dogs(user: dict) -> bool:
    species = [normalize(str(s)).strip() for s in (user.get("farm") or {}).get("species", [])]
    return any(s in DOG_WORDS for s in species)


def _layer(status: str, reason: str, **extra) -> dict:
    return {"status": status, "reason": reason, "updated_at": _now(), **extra}


def _empty(user: dict) -> dict:
    record = {"user_id": user["id"],
              "phone": _layer("not_started", "Confirm your mobile number with a one-time code."),
              "facility": _layer("not_started", "Add 1 to 5 photos of where the animals live.")}
    if breeds_dogs(user):
        record["certificate"] = _layer("not_started", "Dog breeders: add your State Animal Welfare Board "
                                                      "registration certificate.")
    else:
        record["certificate"] = _layer("not_required", "Only dog breeders need a registration certificate.")
    return record


def _overall(record: dict) -> tuple[str, list[str]]:
    required = [k for k in LAYERS if record[k]["status"] != "not_required"]
    failed = [record[k]["reason"] for k in required if record[k]["status"] == "fail"]
    if failed:
        return "rejected", failed
    if all(record[k]["status"] == "pass" for k in required):
        return "verified", []
    return "pending", [record[k]["reason"] for k in required if record[k]["status"] != "pass"]


def _save(user: dict, record: dict) -> dict:
    record["status"], record["open_items"] = _overall(record)
    record["updated_at"] = _now()
    store = deps.get_store()
    store.put(COLLECTION, user["id"], record)
    if user.get("verification_status") != record["status"]:     # shown on listing cards and breeder pages
        user["verification_status"] = record["status"]
        store.save_user(user["id"], user)
    return status_of(user["id"])


def _record(user: dict) -> dict:
    record = deps.get_store().fetch(COLLECTION, user["id"]) or _empty(user)
    if record["certificate"]["status"] == "not_required" and breeds_dogs(user):   # farm now lists dogs
        record["certificate"] = _empty(user)["certificate"]
    return record


def status_of(user_id: str) -> dict:
    user = _user(user_id)
    record = _record(user)
    record["status"], record["open_items"] = _overall(record)
    return {"status": "ok", "verification": record, "dog_breeder": breeds_dogs(user),
            "note": "Phone codes and the registration registry are simulated in this prototype."}


# ---------------------------------------------------------------- layer 1: phone
def request_phone_code(user_id: str, phone: str) -> dict:
    from breedernear_core.accounts import AccountError, normalize_login

    _user(user_id)
    try:
        login, kind = normalize_login(phone)
    except AccountError as e:
        raise ListingError(str(e)) from e
    if kind != "mobile":
        raise ListingError("Please enter a 10-digit Indian mobile number.")
    try:
        return otp_service.request("phone", f"{user_id}:{login}") | {"phone": login}
    except otp_service.OtpError as e:
        raise ListingError(str(e)) from e


def confirm_phone(user_id: str, phone: str, code: str) -> dict:
    from breedernear_core.accounts import AccountError, normalize_login

    user = _user(user_id)
    try:
        login, _ = normalize_login(phone)
        otp_service.verify("phone", f"{user_id}:{login}", code)
    except (AccountError, otp_service.OtpError) as e:
        raise ListingError(str(e)) from e
    record = _record(user)
    record["phone"] = _layer("pass", "Mobile number confirmed.", masked=f"{login[:3]}•••••{login[-3:]}")
    return _save(user, record)


# ---------------------------------------------------------------- layer 2: facility photos
def _take_images(user_id: str, upload_ids: list[str]) -> list[tuple[bytes, str]]:
    images = []
    for upload_id in upload_ids:
        found = deps.get_uploads().get(user_id, upload_id)
        if found is None:
            raise ListingError(f"Photo {upload_id} was not found. Please upload it again.")
        images.append(found)
    return images


def _forget(user_id: str, upload_ids: list[str]) -> None:
    for upload_id in upload_ids:
        deps.get_uploads().delete(user_id, upload_id)


def review_facility(user_id: str, upload_ids: list[str]) -> dict:
    user = _user(user_id)
    if not 1 <= len(upload_ids) <= MAX_FACILITY_PHOTOS:
        raise ListingError("Add 1 to 5 photos of your aviary, cages, kennel or rooms.")
    try:
        review = deps.get_vision().review_facility(_take_images(user_id, upload_ids))
    finally:
        _forget(user_id, upload_ids)
    problems = []
    if review.looks_like_stock_or_screenshot:
        problems.append("the photos look like stock images or screenshots, not your own facility")
    if not review.shows_animal_housing:
        problems.append("the photos don't show where the animals are kept")
    if review.overcrowded:
        problems.append("the animals look overcrowded")
    if review.cleanliness == "dirty":
        problems.append("the housing doesn't look clean")
    if review.space == "cramped":
        problems.append("the space looks too small for the animals")
    if review.animal_condition == "concerning":
        problems.append("some animals show visible signs of concern")
    unclear = review.space == "unclear" or review.cleanliness == "unclear"
    if problems:
        layer = _layer("fail", "Facility photos: " + "; ".join(problems)
                       + ". Improve this and add new photos.")
    elif unclear:
        layer = _layer("pending", "Facility photos are unclear. Add brighter photos of the whole space.")
    else:
        layer = _layer("pass", "Facility photos show clean, roomy housing.")
    layer["observations"] = review.observations[:6]
    record = _record(user)
    record["facility"] = layer
    return _save(user, record)


# ---------------------------------------------------------------- layer 3: registration certificate
def _same_name(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    stop = {"the", "and", "pvt", "ltd", "private", "limited", "kennel", "kennels", "farm", "farms", "home"}
    wa = {w for w in normalize(a).split() if w not in stop and len(w) > 1}
    wb = {w for w in normalize(b).split() if w not in stop and len(w) > 1}
    return bool(wa and wb and (wa <= wb or wb <= wa or len(wa & wb) >= 2))


def review_certificate(user_id: str, upload_id: str, today: date | None = None) -> dict:
    user = _user(user_id)
    if not breeds_dogs(user):
        raise ListingError("Only dog breeders need a registration certificate. Add dogs to your farm "
                           "profile first.")
    try:
        cert = deps.get_vision().read_certificate(_take_images(user_id, [upload_id]))
    finally:
        _forget(user_id, [upload_id])
    today = today or date.today()
    farm = user.get("farm") or {}
    entry = registry_entry(cert.registration_no)
    if not cert.is_breeder_certificate:
        layer = _layer("fail", "That file is not a dog-breeder registration certificate.")
    elif not cert.readable or not cert.registration_no:
        layer = _layer("pending", "The certificate number couldn't be read. Add a sharper photo.")
    elif entry is None:
        layer = _layer("fail", f"Registration {cert.registration_no} is not in the (simulated) registry.")
    elif date.fromisoformat(entry["valid_until"]) < today or (
            cert.valid_until and cert.valid_until[:10] < today.isoformat()):
        layer = _layer("fail", f"Registration {cert.registration_no} has expired. Renew it, then upload "
                               "again.")
    elif not (_same_name(cert.holder_name, user.get("name"))
              or _same_name(cert.holder_name, farm.get("farm_name"))
              or _same_name(entry["name"], farm.get("farm_name"))):
        layer = _layer("fail", "The certificate is issued to a different breeder. Certificates can't be "
                               "transferred; use the one issued to you or your kennel.")
    elif (farm.get("sawb_registration_no")
          and farm["sawb_registration_no"].upper() != cert.registration_no.upper()):
        layer = _layer("fail", "The certificate number doesn't match the number in your farm profile.")
    else:
        layer = _layer("pass", f"Registration {cert.registration_no} is valid until {entry['valid_until']} "
                               "(simulated registry).", registration_no=cert.registration_no)
    record = _record(user)
    record["certificate"] = layer
    return _save(user, record)


def is_verified(user_id: str | None) -> bool:
    if not user_id:
        return False
    user = deps.get_store().get_user(user_id)
    return bool(user and user.get("verification_status") == "verified")
