import pytest
from conftest import DEVICE

from breedernear_core import accounts, care_service, directory_service, listing_service, match_service
from breedernear_core import default_accounts as d
from breedernear_core.catalog import seed_listings


@pytest.fixture
def defaults(fakes):
    store = fakes[0]
    for listing in seed_listings():
        store.save_listing(listing["id"], listing)
    d.seed_default_accounts(store)
    return store


def test_both_default_accounts_log_in_with_the_documented_password(defaults):
    _, seller = accounts.login(d.SELLER_LOGIN, d.PASSWORD, DEVICE)
    _, customer = accounts.login(d.CUSTOMER_LOGIN, d.PASSWORD, DEVICE)
    assert (seller["role"], seller["farm"]["farm_name"]) == ("seller", "Karthik's Aviary")
    assert (customer["role"], customer["district"]) == ("customer", "tiruppur")


def test_seller_dashboard_is_preloaded(defaults):
    dash = listing_service.seller_dashboard(d.SELLER_ID)
    c = dash["counts"]
    assert (c["active"], c["paused"], c["sold"], c["enquiries"], c["views"]) == (2, 1, 1, 4, 85)
    assert dash["recent_activity"]


def test_customer_is_preloaded(defaults):
    assert len(match_service.sent_enquiries(d.CUSTOMER_ID)["enquiries"]) == 2
    assert len(care_service.view_cart(d.CUSTOMER_ID)["items"]) == 4


def test_seller_listings_stay_public_and_in_the_directory(defaults):
    other = match_service.browse_pets("someone-else", "Coimbatore", "budgie")["results"]
    assert "LST-0001" in {c["listing_id"] for c in other}
    assert "LST-0004" not in {c["listing_id"] for c in other}          # sold listings are hidden
    karthik = directory_service.get_breeder("someone-else", d.SELLER_BREEDER_ID)
    assert karthik["breeder"]["pets_for_sale"] == 2


def test_demo_buttons_use_the_default_accounts(defaults):
    _, seller = accounts.demo("seller", DEVICE)
    _, customer = accounts.demo("customer", "bbbbbbbb-1111-4e8b-9c0a-1234567890ab")
    assert seller["id"] == d.SELLER_ID and customer["id"] == d.CUSTOMER_ID


def test_default_accounts_are_protected(defaults):
    seller = accounts.authenticate(accounts.login(d.SELLER_LOGIN, d.PASSWORD, DEVICE)[0])
    with pytest.raises(accounts.AccountError):
        accounts.delete_account(seller)
    with pytest.raises(accounts.AccountError):
        accounts.update_profile(seller, {"farm": {"farm_name": "Hacked"}})
    with pytest.raises(listing_service.ListingError, match="Pause"):
        listing_service.delete_listing(d.SELLER_ID, "LST-0001")
    assert listing_service.set_listing_status(d.SELLER_ID, "LST-0001", "PAUSED")["listing_status"] == "PAUSED"
    accounts.update_profile(seller, {"district": "Erode"})               # district may change


def test_reseeding_resets_without_duplicates(defaults):
    listing_service.set_listing_status(d.SELLER_ID, "LST-0001", "SOLD")
    d.seed_default_accounts(defaults)
    d.seed_default_accounts(defaults)
    assert defaults.get_listing("LST-0001")["status"] == "PUBLISHED"
    assert len([e for e in defaults.all_enquiries() if e["id"].startswith("ENQ_DEMO")]) == 4


def test_reset_removes_what_visitors_added(defaults):
    visitor = {"id": "LST_visitor", "owner_user_id": d.SELLER_ID, "status": "PUBLISHED"}
    defaults.save_listing("LST_visitor", visitor)
    defaults.save_enquiry("ENQ_visitor", {"id": "ENQ_visitor", "listing_id": "LST-0001",
                                          "listing_owner_user_id": d.SELLER_ID, "buyer_user_id": "USR_x"})
    defaults.save_enquiry("ENQ_other", {"id": "ENQ_other", "listing_id": "LST-0009",
                                        "listing_owner_user_id": "USR_other", "buyer_user_id": "USR_y"})
    match_service.send_reply(d.SELLER_ID, "ENQ_DEMO_1", "A reply a visitor sent")
    d.seed_default_accounts(defaults)
    assert defaults.get_listing("LST_visitor") is None and defaults.get_listing("LST-0001")
    ids = {e["id"] for e in defaults.all_enquiries()}
    assert "ENQ_visitor" not in ids and "ENQ_other" in ids and {e[0] for e in d.ENQUIRIES} <= ids
    assert defaults.get_enquiry("ENQ_DEMO_1").get("reply") is None
