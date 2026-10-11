"""F21: one-time-code sign-in (new and demo accounts only) and Google sign-in via Firebase ID tokens."""

import pytest
from conftest import DEVICE
from fastapi.testclient import TestClient

from app.main import app
from breedernear_core import accounts
from breedernear_core import default_accounts as d
from breedernear_core.accounts import AccountError
from breedernear_core.catalog import seed_listings

client = TestClient(app)


@pytest.fixture
def defaults(fakes):
    store = fakes[0]
    for listing in seed_listings():
        store.save_listing(listing["id"], listing)
    d.seed_default_accounts(store)
    return store


def test_code_signup_creates_a_passwordless_account(fakes):
    sent = accounts.request_login_code("new.buyer@example.com")
    assert sent["new_account"] and len(sent["demo_code"]) == 6
    token, user = accounts.login_with_code(
        "new.buyer@example.com", sent["demo_code"], DEVICE, "customer", "Nila"
    )
    assert token and user["role"] == "customer" and user["login_type"] == "email"
    with pytest.raises(AccountError):
        accounts.login("new.buyer@example.com", "anything", DEVICE)  # no password to guess


def test_code_never_opens_an_existing_account(fakes):
    accounts.signup("customer", "Asha", "asha@example.com", "secret123", None, DEVICE)
    with pytest.raises(AccountError) as e:
        accounts.request_login_code("asha@example.com")
    assert e.value.status == 409


def test_demo_accounts_can_use_a_code(defaults):
    sent = accounts.request_login_code(d.CUSTOMER_LOGIN)
    assert not sent["new_account"]
    _, user = accounts.login_with_code(d.CUSTOMER_LOGIN, sent["demo_code"], DEVICE)
    assert user["id"] == d.CUSTOMER_ID


def test_missing_details_do_not_spend_the_code(fakes):
    sent = accounts.request_login_code("9876543210")
    with pytest.raises(AccountError) as e:
        accounts.login_with_code("9876543210", sent["demo_code"], DEVICE)
    assert e.value.status == 422
    _, user = accounts.login_with_code(
        "+91 98765 43210",
        sent["demo_code"],
        DEVICE,
        "seller",
        "Ravi",
        farm={"farm_name": "Ravi Birds", "species": ["budgerigar"]},
    )
    assert user["role"] == "seller" and user["farm"]["farm_name"] == "Ravi Birds"


def google(monkeypatch, **claims):
    monkeypatch.setattr(accounts, "verify_google_token", lambda token: {"email_verified": True, **claims})


def test_google_creates_then_signs_in(fakes, monkeypatch):
    google(monkeypatch, email="Meena@Example.com", name="Meena")
    with pytest.raises(AccountError) as e:
        accounts.login_with_google("tok", DEVICE)
    assert e.value.status == 422  # buy or sell?
    _, user = accounts.login_with_google("tok", DEVICE, "customer")
    assert (user["login"], user["name"]) == ("meena@example.com", "Meena")
    _, again = accounts.login_with_google("tok", DEVICE)
    assert again["id"] == user["id"]


def test_google_signs_in_an_existing_password_account_by_verified_email(fakes, monkeypatch):
    _, asha = accounts.signup("customer", "Asha", "asha@example.com", "secret123", None, DEVICE)
    google(monkeypatch, email="asha@example.com")
    assert accounts.login_with_google("tok", DEVICE)[1]["id"] == asha["id"]


def test_google_needs_a_verified_email(fakes, monkeypatch):
    monkeypatch.setattr(
        accounts, "verify_google_token", lambda t: {"email": "x@example.com", "email_verified": False}
    )
    with pytest.raises(AccountError):
        accounts.login_with_google("tok", DEVICE, "customer", "X")


def test_bad_google_tokens_are_refused(fakes):
    with pytest.raises(AccountError) as e:
        accounts.verify_google_token("not-a-real-token")
    assert e.value.status == 401


def test_routes(fakes, monkeypatch):
    r = client.post("/api/auth/code/request", json={"login": "route@example.com"})
    code = r.json()["demo_code"]
    r = client.post(
        "/api/auth/code/verify",
        headers={"X-Device-Id": DEVICE},
        json={"login": "route@example.com", "code": code, "role": "customer", "name": "Route"},
    )
    assert r.status_code == 200 and r.json()["token"]
    google(monkeypatch, email="g@example.com", name="G User")
    r = client.post(
        "/api/auth/google",
        headers={"X-Device-Id": DEVICE},
        json={"id_token": "t", "role": "seller", "farm": {"farm_name": "G Farm", "species": []}},
    )
    assert r.status_code == 200 and r.json()["user"]["role"] == "seller"
