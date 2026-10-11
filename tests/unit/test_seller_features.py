"""F14 seller analytics, F15 breeder verification, and the one-time codes they use."""

from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import DEVICE, auth_headers, make_image
from fastapi.testclient import TestClient

from app.main import app
from breedernear_core import accounts, analytics_service, deps, otp_service, verification_service
from breedernear_core.listing_service import ListingError
from breedernear_core.schemas import CertificateRead, FacilityReview

client = TestClient(app)


def new_seller(name="Ravi", farm_name="Ravi Birds", species=("budgerigar",)):
    login = f"{farm_name.split()[0].lower()}@example.com"
    _, user = accounts.signup("seller", name, login, "secret123", "coimbatore", DEVICE,
                              farm={"farm_name": farm_name, "species": list(species)})
    return user["id"]


def upload(user_id, kind="facility_photo"):
    return deps.get_uploads().put(user_id, make_image(1), "image/jpeg", kind)


# ---------------------------------------------------------------- one-time codes
def test_code_works_once(fakes):
    sent = otp_service.request("login", "a@example.com")
    assert len(sent["demo_code"]) == 6 and "simulated" in sent["delivery"]
    otp_service.verify("login", "a@example.com", sent["demo_code"])
    with pytest.raises(otp_service.OtpError):
        otp_service.verify("login", "a@example.com", sent["demo_code"])


def test_wrong_codes_lock_and_resend_is_throttled(fakes):
    sent = otp_service.request("login", "b@example.com")
    with pytest.raises(otp_service.OtpError) as resend:
        otp_service.request("login", "b@example.com")
    assert resend.value.status == 429
    wrong = "000000" if sent["demo_code"] != "000000" else "111111"
    for _ in range(otp_service.MAX_TRIES):
        with pytest.raises(otp_service.OtpError):
            otp_service.verify("login", "b@example.com", wrong)
    with pytest.raises(otp_service.OtpError):                  # locked even with the right code
        otp_service.verify("login", "b@example.com", sent["demo_code"])


def test_codes_expire_and_are_stored_hashed(fakes, monkeypatch):
    sent = otp_service.request("login", "c@example.com")
    record = fakes[0].find("otps")[0]
    assert sent["demo_code"] not in str(record)
    later = datetime.now(UTC) + timedelta(minutes=6)
    monkeypatch.setattr(otp_service, "_now", lambda: later)
    with pytest.raises(otp_service.OtpError, match="expired"):
        otp_service.verify("login", "c@example.com", sent["demo_code"])


# ---------------------------------------------------------------- verification
def test_new_bird_breeder_starts_pending_without_certificate(fakes):
    v = verification_service.status_of(new_seller())["verification"]
    assert v["status"] == "pending"
    assert (v["phone"]["status"], v["facility"]["status"], v["certificate"]["status"]) == (
        "not_started", "not_started", "not_required")


def test_phone_and_facility_make_a_bird_breeder_verified(fakes):
    uid = new_seller()
    code = verification_service.request_phone_code(uid, "98765 43210")["demo_code"]
    verification_service.confirm_phone(uid, "9876543210", code)
    photos = [upload(uid), upload(uid)]
    r = verification_service.review_facility(uid, photos)
    assert r["verification"]["status"] == "verified"
    assert fakes[2].calls[-1] == "facility:2"
    assert all(deps.get_uploads().get(uid, p) is None for p in photos)        # photos deleted once read
    assert fakes[0].get_user(uid)["verification_status"] == "verified"
    assert "9876543210" not in str(r)                                          # number stored masked


@pytest.mark.parametrize("change, status, words", [
    ({"looks_like_stock_or_screenshot": True}, "fail", "stock"),
    ({"overcrowded": True}, "fail", "overcrowded"),
    ({"cleanliness": "dirty"}, "fail", "clean"),
    ({"space": "unclear"}, "pending", "unclear"),
])
def test_facility_rules_are_in_code(fakes, change, status, words):
    uid = new_seller()
    fakes[2].facility = FacilityReview(**(fakes[2].facility.model_dump() | change))
    layer = verification_service.review_facility(uid, [upload(uid)])["verification"]["facility"]
    assert layer["status"] == status and words in layer["reason"]


def test_facility_photo_count(fakes):
    uid = new_seller()
    with pytest.raises(ListingError):
        verification_service.review_facility(uid, [])
    with pytest.raises(ListingError):
        verification_service.review_facility(uid, [upload(uid) for _ in range(6)])


def dog_seller():
    return new_seller("Arun", "Kovai Paws Kennel", ("labrador",))


def test_dog_breeder_needs_a_valid_certificate_issued_to_them(fakes):
    uid = dog_seller()
    assert verification_service.status_of(uid)["verification"]["certificate"]["status"] == "not_started"
    cert_upload = upload(uid, "certificate")
    r = verification_service.review_certificate(uid, cert_upload, date(2026, 10, 11))
    layer = r["verification"]["certificate"]
    assert layer["status"] == "pass" and "SIM-TNAWB-DB-0042" in layer["reason"]
    assert deps.get_uploads().get(uid, cert_upload) is None


@pytest.mark.parametrize("change, today, words", [
    ({"is_breeder_certificate": False}, date(2026, 10, 11), "not a dog-breeder"),
    ({"registration_no": "SIM-XX-0000"}, date(2026, 10, 11), "not in the"),
    ({}, date(2027, 6, 1), "expired"),
    ({"holder_name": "Someone Else"}, date(2026, 10, 11), "different breeder"),
])
def test_certificate_failures(fakes, change, today, words):
    uid = new_seller("Meena", "Meena Pups", ("labrador",))
    fakes[2].certificate = CertificateRead(**(fakes[2].certificate.model_dump() | change))
    r = verification_service.review_certificate(uid, upload(uid, "certificate"), today)
    layer = r["verification"]["certificate"]
    assert layer["status"] == "fail" and words in layer["reason"]


def test_bird_breeder_cannot_submit_a_certificate(fakes):
    uid = new_seller()
    with pytest.raises(ListingError):
        verification_service.review_certificate(uid, upload(uid, "certificate"))


def test_customers_cannot_be_verified(fakes):
    _, buyer = accounts.signup("customer", "Asha", "asha@example.com", "secret123", "tiruppur", DEVICE)
    with pytest.raises(ListingError):
        verification_service.status_of(buyer["id"])


# ---------------------------------------------------------------- analytics
def test_events_become_weekly_series(fakes):
    uid = new_seller()
    listing = {"id": "LST-X", "draft": {"species_common": "Lovebird"}}
    now = datetime.now(UTC)
    for kind, amount in (("view", 0), ("view", 0), ("enquiry", 0), ("visit", 0), ("sale", 1800)):
        analytics_service.record(uid, listing, kind, amount, now)
    analytics_service.record(uid, listing, "view", 0, now - timedelta(weeks=20))          # outside the window
    analytics_service.record(None, listing, "view")                    # sample listing: ignored
    s = analytics_service.summary(uid, now.date())
    assert s["totals"] == {"views": 2, "enquiries": 1, "visits": 1, "sales": 1, "revenue_inr": 1800,
                           "enquiry_rate_pct": 50.0}
    assert s["activity"]["view"][-1] == 2 and len(s["weeks"]) == 8
    assert s["revenue_by_species"] == [{"species": "Lovebird", "amount_inr": 1800}]
    assert [f["count"] for f in s["funnel"]] == [2, 1, 1, 1]


def test_viewing_and_enquiring_record_events_for_the_owner(seeded):
    from breedernear_core import match_service
    uid = new_seller()
    store = seeded[0]
    listing = store.get_listing("LST-0001")
    store.save_listing("LST-0001", {**listing, "owner_user_id": uid})
    match_service.get_listing("buyer-1", "LST-0001")
    match_service.create_enquiry("buyer-1", "LST-0001", "Is it available?")
    assert analytics_service.summary(uid)["totals"]["views"] == 1
    assert analytics_service.summary(uid)["totals"]["enquiries"] == 1


# ---------------------------------------------------------------- API
def test_seller_routes(seeded):
    seller, customer = auth_headers(client, "seller"), auth_headers(client, "customer")
    assert client.get("/api/seller/analytics", headers=customer).status_code == 403
    assert client.get("/api/seller/analytics", headers=seller).status_code == 200
    v = client.get("/api/seller/verification", headers=seller).json()["verification"]
    assert v["status"] == "pending"
    r = client.post("/api/seller/verification/phone/request", headers=seller, json={"phone": "9876543210"})
    code = r.json()["demo_code"]
    r = client.post("/api/seller/verification/phone/verify", headers=seller,
                    json={"phone": "9876543210", "code": code})
    assert r.json()["verification"]["phone"]["status"] == "pass"
    up = client.post("/api/uploads", headers=seller, data={"kind": "facility_photo"},
                     files={"file": ("f.jpg", make_image(2), "image/jpeg")}).json()["upload_id"]
    r = client.post("/api/seller/verification/facility", headers=seller, json={"upload_ids": [up]})
    assert r.status_code == 200 and r.json()["verification"]["status"] == "verified"


def test_upload_kinds_follow_roles(seeded):
    customer = auth_headers(client, "customer")
    r = client.post("/api/uploads", headers=customer, data={"kind": "certificate"},
                    files={"file": ("c.jpg", make_image(3), "image/jpeg")})
    assert r.status_code == 403
