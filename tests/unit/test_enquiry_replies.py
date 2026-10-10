"""F8: the seller replies to an enquiry, with a draft written by AI from the listing's facts."""

import pytest
from conftest import auth_headers
from fastapi.testclient import TestClient

from app.main import app
from breedernear_core import default_accounts as d
from breedernear_core import match_service as svc
from breedernear_core.catalog import seed_listings
from breedernear_core.guardrails import unsafe_reply
from breedernear_core.listing_service import ListingError
from breedernear_core.schemas import EnquiryReply

client = TestClient(app)


@pytest.fixture
def defaults(fakes):
    store = fakes[0]
    for listing in seed_listings():
        store.save_listing(listing["id"], listing)
    d.seed_default_accounts(store)
    return fakes


def test_draft_uses_listing_facts_and_the_buyer_message(defaults):
    vision = defaults[2]
    r = svc.draft_reply(d.SELLER_ID, "ENQ_DEMO_1", "Karthik's Aviary")
    assert r["reply"].startswith("Yes, the pair is available") and r["needs_seller_input"] == ["visit times"]
    facts = vision.reply_calls[-1]
    assert "Karthik's Aviary" in facts and "Lovebird" in facts and "Lutino" in facts
    assert "lutino lovebirds still available" in facts            # the buyer's own words


def test_unsafe_draft_falls_back_to_a_safe_reply(defaults):
    defaults[2].reply = EnquiryReply(reply="Give them 5 mg of doxycycline daily.")
    r = svc.draft_reply(d.SELLER_ID, "ENQ_DEMO_1", "Karthik's Aviary")
    assert unsafe_reply(r["reply"]) is None and "visit" in r["reply"]


def test_only_the_listing_owner_can_draft_or_reply(defaults):
    with pytest.raises(ListingError):
        svc.draft_reply(d.CUSTOMER_ID, "ENQ_DEMO_1")
    with pytest.raises(ListingError):
        svc.send_reply("USR_SOMEONE_ELSE", "ENQ_DEMO_1", "Hello")


def test_reply_reaches_the_buyer_and_shows_in_the_seller_inbox(defaults):
    svc.send_reply(d.SELLER_ID, "ENQ_DEMO_1", "Yes, available. Please visit on Saturday morning.")
    sent = {e["enquiry_id"]: e for e in svc.sent_enquiries(d.CUSTOMER_ID)["enquiries"]}
    assert sent["ENQ_DEMO_1"]["reply"]["text"].startswith("Yes, available")
    inbox = {e["enquiry_id"]: e for e in svc.my_enquiries(d.SELLER_ID)["enquiries"]}
    assert inbox["ENQ_DEMO_1"]["reply"] and inbox["ENQ_DEMO_2"]["reply"] is None
    assert "buyer_user_id" not in inbox["ENQ_DEMO_1"]            # no buyer identity in the seller's view


@pytest.mark.parametrize("text", ["", "   ", "x" * (svc.MAX_REPLY_CHARS + 1)])
def test_empty_or_long_replies_are_refused(defaults, text):
    with pytest.raises(ListingError):
        svc.send_reply(d.SELLER_ID, "ENQ_DEMO_1", text)


def test_reply_api_roles(defaults):
    seller, customer = auth_headers(client, "seller"), auth_headers(client, "customer")
    r = client.post("/api/seller/enquiries/ENQ_DEMO_1/draft-reply", headers=seller)
    assert r.status_code == 200 and r.json()["reply"]
    assert client.post("/api/seller/enquiries/ENQ_DEMO_1/draft-reply", headers=customer).status_code == 403
    assert client.post("/api/seller/enquiries/ENQ_NOPE/draft-reply", headers=seller).status_code == 404
    reply = {"text": "See you Saturday."}
    r = client.post("/api/seller/enquiries/ENQ_DEMO_1/reply", headers=seller, json=reply)
    assert r.status_code == 200 and r.json()["enquiry"]["reply"]["text"] == "See you Saturday."
    sent = client.get("/api/enquiries/sent", headers=customer).json()["enquiries"]
    assert any(e["reply"] and e["reply"]["text"] == "See you Saturday." for e in sent)
