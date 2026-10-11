"""One-time codes: sign-in by email or mobile, and confirming a seller's phone number.

Delivery is SIMULATED: no SMS or email provider is connected in this prototype, so the code is returned to
the app and shown on screen, labelled as a demo. Everything else is real: codes are random, stored only as
salted hashes, expire after 5 minutes, lock after 5 wrong tries, and can be re-sent at most every 20 seconds.
Replace `_deliver` with an SMS/email sender to go live.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from breedernear_core import deps

COLLECTION = "otps"
TTL = timedelta(minutes=5)
RESEND_AFTER = timedelta(seconds=20)
MAX_TRIES = 5
PURPOSES = {"login", "phone"}


class OtpError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _now() -> datetime:
    return datetime.now(UTC)


def _key(purpose: str, target: str) -> str:
    return hashlib.sha256(f"{purpose}:{target}".encode()).hexdigest()


def _hash(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def _deliver(target: str, code: str) -> dict:
    """Simulated delivery: hand the code back to the app. A real sender would return {} here."""
    return {"demo_code": code,
            "delivery": "simulated: shown on screen (no SMS or email provider in this demo)"}


def request(purpose: str, target: str) -> dict:
    if purpose not in PURPOSES:
        raise OtpError("Unknown code purpose.")
    store, key, now = deps.get_store(), _key(purpose, target), _now()
    old = store.fetch(COLLECTION, key)
    if old and now - datetime.fromisoformat(old["sent_at"]) < RESEND_AFTER:
        raise OtpError("Please wait a few seconds before asking for another code.", 429)
    code, salt = f"{secrets.randbelow(10**6):06d}", secrets.token_hex(8)
    store.put(COLLECTION, key, {"purpose": purpose, "salt": salt, "code_hash": _hash(code, salt), "tries": 0,
                                "sent_at": now.isoformat(), "expires_at": (now + TTL).isoformat()})
    return {"status": "ok", "expires_in_seconds": int(TTL.total_seconds()), **_deliver(target, code)}


def verify(purpose: str, target: str, code: str) -> None:
    """Raises OtpError unless the code is right; a used code can't be used again."""
    store, key = deps.get_store(), _key(purpose, target)
    record = store.fetch(COLLECTION, key)
    if record is None:
        raise OtpError("Ask for a code first.")
    if _now() > datetime.fromisoformat(record["expires_at"]):
        store.remove(COLLECTION, key)
        raise OtpError("That code has expired. Ask for a new one.")
    if record["tries"] >= MAX_TRIES:
        store.remove(COLLECTION, key)
        raise OtpError("Too many wrong tries. Ask for a new code.", 429)
    if not hmac.compare_digest(record["code_hash"], _hash(code.strip(), record["salt"])):
        record["tries"] += 1
        store.put(COLLECTION, key, record)
        raise OtpError("That code is not right.")
    store.remove(COLLECTION, key)
