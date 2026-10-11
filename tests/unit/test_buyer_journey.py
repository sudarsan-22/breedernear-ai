"""F16 profile and compatibility, F17 first message and scam shield, F18 visits and purchase, F19 vaccination
card, F20 care companion."""

from datetime import date, timedelta

import pytest
from conftest import DEVICE, auth_headers, make_image
from fastapi.testclient import TestClient

from app.main import app
from breedernear_core import (
    accounts,
    analytics_service,
    buyer_service,
    companion_service,
    deps,
    journey_service,
    listing_service,
    match_service,
)
from breedernear_core.guardrails import MEDICINE_REPLY
from breedernear_core.listing_service import ListingError
from breedernear_core.safety.trust_score import ScreeningInputs, screen
from breedernear_core.schemas import (
    CareSuggestion,
    ListingDraft,
    MessageScan,
    OpeningMessage,
    SymptomCheck,
    VaccinationRead,
)

client = TestClient(app)
TODAY = date.today()


def buyer(name="Asha"):
    _, user = accounts.signup(
        "customer", name, f"{name.lower()}@example.com", "secret123", "tiruppur", DEVICE
    )
    return user["id"]


def owned_listing(store, owner_id, listing_id="LST-0002", count=2):
    listing = store.get_listing(listing_id)
    listing["draft"]["count"] = count
    store.save_listing(listing_id, {**listing, "owner_user_id": owner_id})
    return listing_id


# ---------------------------------------------------------------- profile and compatibility (code)
def test_profile_from_words_and_fields(fakes):
    uid = buyer()
    r = buyer_service.save_profile(uid, {"budget_inr": 2500}, "Flat in Tiruppur, 8 year old daughter")
    assert fakes[2].calls[-1].startswith("profile:Flat in Tiruppur")
    assert r["profile"]["budget_inr"] == 2500 and r["profile"]["has_young_children"] is True  # fields win
    pct = {s["species_key"]: s for s in r["compatibility"]}
    assert pct["budgerigar"]["percent"] > 80
    assert pct["labrador"]["percent"] == 0 and pct["labrador"]["watch_outs"]


def test_profile_needs_something(fakes):
    with pytest.raises(ListingError):
        buyer_service.save_profile(buyer())


def test_compatibility_rules_are_explainable(fakes):
    from breedernear_core.match_service import _species

    sp = {s["key"]: s for s in _species()}
    base = buyer_service.BuyerProfile(
        home_type="house", first_time_owner=False, time_per_day_minutes=240
    ).model_dump()
    cat_ok = buyer_service.score_species(sp["persian_cat"], base)[0]
    cat_allergy, _, cons = buyer_service.score_species(sp["persian_cat"], base | {"allergies": True})
    assert cat_allergy == cat_ok - 25 and "allergies" in cons[-1]
    lab = buyer_service.score_species(sp["labrador"], base | {"hours_away_per_day": 10, "activity": "low"})
    assert lab[0] < buyer_service.score_species(sp["labrador"], base | {"activity": "high"})[0]
    assert any("alone" in c for c in lab[2])


def test_no_profile_gives_no_percentages(fakes):
    assert buyer_service.compatibility(buyer())["species"] == []


# ---------------------------------------------------------------- first message and scam shield
def test_opening_message_uses_listing_and_profile(seeded):
    uid = buyer()
    buyer_service.save_profile(uid, {"home_type": "flat"})
    msg = buyer_service.opening_message(uid, "LST-0002")["message"]
    assert msg == seeded[2].opening.message
    assert "Lovebird" in seeded[2].calls[-1] and "flat" in seeded[2].calls[-1]


@pytest.mark.parametrize("bad", ["Give 5 mg of doxycycline first.", "Pay full advance on GPay first please."])
def test_unsafe_opening_message_is_replaced(seeded, bad):
    seeded[2].opening = OpeningMessage(message=bad)
    msg = buyer_service.opening_message(buyer(), "LST-0002")["message"]
    assert msg.startswith("Hello! Is your lovebird still available")


def test_scam_rules_work_without_the_model(fakes, monkeypatch):
    def broken(text):
        raise RuntimeError("model down")

    monkeypatch.setattr(fakes[2], "scan_message", broken)
    r = buyer_service.scan_text("Full advance only, courier only. Send the OTP you get.")
    assert r["risk"] == "high" and any("OTP" in s for s in r["signals"])


def test_model_adds_signals(fakes):
    fakes[2].scan = MessageScan(risk="low", signals=["moves the chat off the platform"])
    r = buyer_service.scan_text("Message me on another app instead")
    assert r == {"risk": "low", "signals": ["moves the chat off the platform"]}


def test_enquiry_and_reply_carry_a_scan(seeded):
    seller = accounts.signup(
        "seller",
        "Ravi",
        "ravi@example.com",
        "secret123",
        "coimbatore",
        DEVICE,
        farm={"farm_name": "Ravi Birds", "species": ["lovebird"]},
    )[1]["id"]
    owned_listing(seeded[0], seller)
    enq = match_service.create_enquiry(
        buyer(), "LST-0002", "Is it available? I can pay full advance only by courier."
    )
    stored = seeded[0].get_enquiry(enq["enquiry_id"])
    assert stored["scan"]["risk"] == "high"
    match_service.send_reply(seller, enq["enquiry_id"], "Yes, please visit on Saturday.")
    assert seeded[0].get_enquiry(enq["enquiry_id"])["reply"]["scan"]["risk"] == "none"


# ---------------------------------------------------------------- visits and purchase
def test_sample_breeder_visit_is_confirmed_and_purchase_starts_the_companion(seeded):
    uid = buyer()
    v = journey_service.request_visit(uid, "LST-0009", (TODAY + timedelta(days=2)).isoformat(), "morning")
    assert v["visit"]["status"] == "confirmed" and "Sample breeder" in v["note"]
    before = seeded[0].get_listing("LST-0009")["draft"]["count"]
    r = journey_service.purchase(uid, v["visit"]["id"], "Mango")
    assert r["pet_name"] == "Mango"
    assert seeded[0].get_listing("LST-0009")["draft"]["count"] == before  # shared sample listing unchanged
    assert companion_service.list_pets(uid)["pets"][0]["name"] == "Mango"
    with pytest.raises(ListingError):
        journey_service.purchase(uid, v["visit"]["id"])  # only once


def test_seller_listing_visit_needs_confirmation_then_sale_updates_listing(seeded):
    store = seeded[0]
    seller = accounts.signup(
        "seller",
        "Ravi",
        "ravi@example.com",
        "secret123",
        "coimbatore",
        DEVICE,
        farm={"farm_name": "Ravi Birds", "species": ["lovebird"]},
    )[1]["id"]
    owned_listing(store, seller, count=1)
    uid = buyer()
    v = journey_service.request_visit(uid, "LST-0002", (TODAY + timedelta(days=3)).isoformat(), "evening")[
        "visit"
    ]
    assert v["status"] == "requested"
    with pytest.raises(ListingError):
        journey_service.purchase(uid, v["id"])  # not confirmed yet
    with pytest.raises(ListingError):
        journey_service.answer_visit("someone-else", v["id"], "confirm")
    journey_service.answer_visit(seller, v["id"], "confirm", "See you then")
    with pytest.raises(ListingError):
        journey_service.purchase(buyer("Other"), v["id"])  # not their visit
    journey_service.purchase(uid, v["id"])
    assert store.get_listing("LST-0002")["status"] == "SOLD"
    totals = analytics_service.summary(seller)["totals"]
    assert (totals["visits"], totals["sales"], totals["revenue_inr"]) == (
        1,
        1,
        store.get_listing("LST-0002")["price_inr"],
    )


@pytest.mark.parametrize(
    "day, slot",
    [
        (TODAY.isoformat(), "morning"),
        ((TODAY + timedelta(days=40)).isoformat(), "morning"),
        ((TODAY + timedelta(days=2)).isoformat(), "midnight"),
        ("soon", "morning"),
    ],
)
def test_visit_date_and_slot_rules(seeded, day, slot):
    with pytest.raises(ListingError):
        journey_service.request_visit(buyer(), "LST-0009", day, slot)


def test_one_open_visit_per_pet(seeded):
    uid = buyer()
    day = (TODAY + timedelta(days=2)).isoformat()
    journey_service.request_visit(uid, "LST-0009", day, "morning")
    with pytest.raises(ListingError):
        journey_service.request_visit(uid, "LST-0009", day, "evening")


# ---------------------------------------------------------------- vaccination card (trust score)
def _draft(group="dog"):
    return ListingDraft(species_common="Labrador Retriever", animal_group=group, price_inr=22000, count=2)


def test_vaccination_checks():
    rec = VaccinationRead(is_vaccination_record=True, readable=True, entries=[{"vaccine": "DHPPi"}])
    ok = screen(
        ScreeningInputs(draft=_draft(), vaccination=rec, sawb_status="valid", price_range=(15000, 30000))
    )
    assert any(c.name == "vaccination" and c.result == "pass" for c in ok.checks)
    wrong = screen(
        ScreeningInputs(
            draft=_draft(),
            vaccination=VaccinationRead(is_vaccination_record=False, readable=True),
            sawb_status="valid",
            price_range=(15000, 30000),
        )
    )
    assert wrong.trust_score == ok.trust_score - 10
    missing = screen(ScreeningInputs(draft=_draft(), sawb_status="valid", price_range=(15000, 30000)))
    assert missing.trust_score == ok.trust_score and any(
        "vaccination" in q for q in missing.questions_to_ask_seller
    )
    bird = screen(ScreeningInputs(draft=_draft("bird")))
    assert not any(c.name == "vaccination" for c in bird.checks)


def test_publish_reads_an_attached_vaccination_card(fakes):
    uid = "seller-1"
    up = deps.get_uploads().put(uid, make_image(4), "image/jpeg", "listing_photo")
    draft_id = listing_service.extract_listing(uid, "4 lutino lovebird pairs", [up])["draft_id"]
    card = deps.get_uploads().put(uid, make_image(5), "image/jpeg", "vaccination")
    listing_service.attach_vaccination(uid, draft_id, card)
    r = listing_service.publish_listing(uid, draft_id)
    assert "vaccination" in fakes[2].calls
    assert any(c["name"] == "vaccination" and c["result"] == "pass" for c in r["screening"]["checks"])


# ---------------------------------------------------------------- care companion
@pytest.fixture
def pet(seeded):
    uid = buyer()
    v = journey_service.request_visit(uid, "LST-0009", (TODAY + timedelta(days=2)).isoformat(), "morning")[
        "visit"
    ]
    pet_id = journey_service.purchase(uid, v["id"], "Mango")["pet_id"]
    return uid, pet_id


def test_daily_log_and_streak(pet, seeded):
    uid, pet_id = pet
    r = companion_service.log_day(uid, pet_id, food="Seed mix and coriander", play="Climbed the ladder")
    assert r["log"]["feedback"] == "A good start." and r["streak"] == 1
    assert "Budgerigar" in seeded[2].calls[-1]
    with pytest.raises(ListingError):
        companion_service.log_day(uid, pet_id)


def test_unsafe_care_feedback_is_replaced(pet, seeded):
    uid, pet_id = pet
    seeded[2].care = CareSuggestion(food_ok=True, feedback="Add 2 drops of enrofloxacin to the water.")
    assert companion_service.log_day(uid, pet_id, food="seeds")["log"]["feedback"] == MEDICINE_REPLY


def test_food_photo_is_deleted_after_review(pet):
    uid, pet_id = pet
    photo = deps.get_uploads().put(uid, make_image(6), "image/jpeg", "food_photo")
    companion_service.log_day(uid, pet_id, photo_upload_id=photo)
    assert deps.get_uploads().get(uid, photo) is None


@pytest.mark.parametrize("grams, words", [(36, "Within"), (22, "Below"), (60, "Above")])
def test_weight_verdicts(pet, grams, words):
    uid, pet_id = pet
    assert companion_service.add_weight(uid, pet_id, grams)["verdict"].startswith(words)


def test_symptom_checker_has_a_code_floor(pet, seeded):
    uid, pet_id = pet
    seeded[2].symptom = SymptomCheck(urgency="monitor", possible_meaning="Could be minor.")
    assert companion_service.check_symptoms(uid, pet_id, "bleeding from the foot")["urgency"] == "emergency"
    assert companion_service.check_symptoms(uid, pet_id, "a bit quiet today")["urgency"] == "vet_soon"  # bird


def test_symptom_checker_never_names_medicines(pet, seeded):
    uid, pet_id = pet
    seeded[2].symptom = SymptomCheck(urgency="vet_soon", possible_meaning="Give doxycycline for this.")
    r = companion_service.check_symptoms(uid, pet_id, "sneezing")
    assert r["possible_meaning"] == MEDICINE_REPLY and "vet" in r["first_step"]


def test_pets_are_private(pet):
    _, pet_id = pet
    with pytest.raises(ListingError):
        companion_service.get_pet(buyer("Other"), pet_id)


def test_pet_page_has_calendar_and_growth(pet):
    uid, pet_id = pet
    companion_service.add_weight(uid, pet_id, 33)
    page = companion_service.get_pet(uid, pet_id)
    assert page["typical_weight"]["unit"] == "g" and page["weights"][0]["range"]
    assert page["calendar"][0]["status"] == "advice" and page["red_flags"]


# ---------------------------------------------------------------- API
def test_buyer_routes_and_roles(seeded):
    seller, customer = auth_headers(client, "seller"), auth_headers(client, "customer")
    assert client.get("/api/buyer/compatibility", headers=seller).status_code == 403
    r = client.post("/api/buyer/profile", headers=customer, json={"words": "flat, first pet"})
    assert r.status_code == 200 and r.json()["compatibility"]
    day = (TODAY + timedelta(days=2)).isoformat()
    v = client.post(
        "/api/visits", headers=customer, json={"listing_id": "LST-0009", "date": day, "slot": "morning"}
    )
    assert v.status_code == 200
    p = client.post(
        "/api/purchases", headers=customer, json={"visit_id": v.json()["visit"]["id"], "pet_name": "Kiwi"}
    )
    pet_id = p.json()["pet_id"]
    assert client.get(f"/api/companion/pets/{pet_id}", headers=customer).status_code == 200
    assert client.get(f"/api/companion/pets/{pet_id}", headers=seller).status_code == 403
    r = client.post(f"/api/companion/pets/{pet_id}/symptoms", headers=customer, json={"text": "sneezing"})
    assert r.json()["urgency"] in ("vet_soon", "emergency")
    assert client.post("/api/listings/LST-0009/opening-message", headers=customer).json()["message"]
    assert client.get("/api/seller/visits", headers=seller).status_code == 200
