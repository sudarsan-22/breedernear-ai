from datetime import UTC, datetime, timedelta

import pytest
from conftest import DEVICE

from breedernear_core import accounts
from breedernear_core.accounts import AccountError

FARM = {
    "farm_name": "Noyyal Birds",
    "seller_type": "home_breeder",
    "locality": "Avinashi Road",
    "species": ["budgerigar"],
}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Priya@Example.COM ", ("priya@example.com", "email")),
        ("98765 43210", ("+919876543210", "mobile")),
        ("+91-9876543210", ("+919876543210", "mobile")),
        ("09876543210", ("+919876543210", "mobile")),
    ],
)
def test_login_normalisation(raw, expected):
    assert accounts.normalize_login(raw) == expected


@pytest.mark.parametrize("raw", ["", "12345", "5876543210", "priya@", "not an email"])
def test_invalid_logins_are_rejected(raw):
    with pytest.raises(AccountError):
        accounts.normalize_login(raw)


def test_passwords_are_salted_hashes():
    a, b = accounts.hash_password("lovebirds123"), accounts.hash_password("lovebirds123")
    assert a != b and "lovebirds123" not in a and a.startswith("scrypt$")
    assert accounts.verify_password("lovebirds123", a) and not accounts.verify_password("wrong-pass", a)
    assert not accounts.verify_password("x", None) and not accounts.verify_password("x", "garbage")


def test_signup_then_login_with_email_or_mobile(fakes):
    store = fakes[0]
    token, user = accounts.signup("customer", "Priya", "9876543210", "lovebirds123", "Tirupur", DEVICE)
    assert user["district"] == "tiruppur" and "password_hash" not in user
    assert "lovebirds123" not in str(store.users)
    assert not any(token in key for key in store.sessions)  # tokens are stored only as hashes
    token2, again = accounts.login("+91 98765 43210", "lovebirds123", DEVICE)
    assert again["id"] == user["id"] and accounts.authenticate(token2)["role"] == "customer"


def test_duplicate_login_is_refused(fakes):
    accounts.signup("customer", "Priya", "priya@example.com", "lovebirds123", None, DEVICE)
    with pytest.raises(AccountError) as e:
        accounts.signup("seller", "Other", "PRIYA@example.com", "another-pass", None, DEVICE, farm=FARM)
    assert e.value.status == 409


def test_wrong_password_and_unknown_user_get_the_same_message(fakes):
    accounts.signup("customer", "Priya", "priya@example.com", "lovebirds123", None, DEVICE)
    with pytest.raises(AccountError) as wrong:
        accounts.login("priya@example.com", "nope-nope", DEVICE)
    with pytest.raises(AccountError) as unknown:
        accounts.login("nobody@example.com", "nope-nope", DEVICE)
    assert str(wrong.value) == str(unknown.value) and wrong.value.status == 401


def test_signup_validation(fakes):
    with pytest.raises(AccountError, match="8 characters"):
        accounts.signup("customer", "Priya", "priya@example.com", "short", None, DEVICE)
    with pytest.raises(AccountError, match="buy or sell"):
        accounts.signup("admin", "Priya", "priya@example.com", "lovebirds123", None, DEVICE)
    with pytest.raises(AccountError, match="farm"):
        accounts.signup("seller", "Karthik", "k@example.com", "lovebirds123", None, DEVICE, farm={})
    # a failed seller sign-up must not reserve the email
    accounts.signup("customer", "Karthik", "k@example.com", "lovebirds123", None, DEVICE)


def test_seller_verification_uses_the_simulated_registry(fakes):
    dogs = FARM | {"species": ["labrador"]}
    _, missing = accounts.signup("seller", "Anbu", "a@example.com", "lovebirds123", None, DEVICE, farm=dogs)
    _, verified = accounts.signup(
        "seller",
        "Bala",
        "b@example.com",
        "lovebirds123",
        None,
        DEVICE,
        farm=dogs | {"sawb_registration_no": "SIM-TNAWB-DB-0042"},
    )
    _, birds = accounts.signup("seller", "Chitra", "c@example.com", "lovebirds123", None, DEVICE, farm=FARM)
    assert (
        missing["farm"]["verification"],
        verified["farm"]["verification"],
        birds["farm"]["verification"],
    ) == ("missing", "verified", "not_required")


def test_sessions_expire_and_logout(fakes):
    store = fakes[0]
    token, _ = accounts.signup(
        "customer", "Priya", "priya@example.com", "lovebirds123", None, DEVICE, remember=False
    )
    key = next(iter(store.sessions))
    assert datetime.fromisoformat(store.sessions[key]["expires_at"]) < datetime.now(UTC) + timedelta(hours=25)
    store.sessions[key]["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(AccountError):
        accounts.authenticate(token)
    token, _ = accounts.login("priya@example.com", "lovebirds123", DEVICE)
    accounts.logout(token)
    with pytest.raises(AccountError):
        accounts.authenticate(token)


def test_demo_accounts_are_private_per_device_and_reused(fakes):
    _, a = accounts.demo("seller", DEVICE)
    _, again = accounts.demo("seller", DEVICE)
    _, other = accounts.demo("seller", "bbbbbbbb-1111-4e8b-9c0a-1234567890ab")
    _, buyer = accounts.demo("customer", DEVICE)
    assert a["id"] == again["id"] and a["id"] != other["id"] and buyer["role"] == "customer"
    assert a["demo"] and a["farm"]["farm_name"]
    with pytest.raises(AccountError):  # no password login into demo accounts
        accounts.login(a["login"], "anything-at-all", DEVICE)


def test_delete_account_removes_everything(fakes):
    store = fakes[0]
    token, user = accounts.signup("seller", "Kumar", "k@example.com", "lovebirds123", None, DEVICE, farm=FARM)
    store.save_listing("LST_x", {"id": "LST_x", "owner_user_id": user["id"]})
    accounts.delete_account(accounts.authenticate(token))
    assert store.users == {} and store.listings == {} and store.sessions == {} and store.logins == {}


def test_role_is_enforced_in_agent_tools(fakes):
    from types import SimpleNamespace

    from breedernear_core.tools.care import add_to_cart
    from breedernear_core.tools.listing import extract_listing

    _, customer = accounts.demo("customer", DEVICE)
    _, seller = accounts.demo("seller", DEVICE)
    as_customer = SimpleNamespace(user_id=customer["id"], state={})
    as_seller = SimpleNamespace(user_id=seller["id"], state={})
    assert extract_listing("4 lovebird pairs", [], as_customer)["status"] == "error"
    assert add_to_cart(["PRD-FOOD-001"], as_seller)["status"] == "error"
    assert extract_listing("4 lovebird pairs", [], as_seller)["status"] == "ok"
