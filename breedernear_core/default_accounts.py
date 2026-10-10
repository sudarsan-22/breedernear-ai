"""Two permanent demo accounts with preloaded data, so judges see a lived-in app.

    Customer: priya.customer@example.com / demo12345
    Seller:   karthik.seller@example.com / demo12345   (owns the sample breeder "Karthik's Aviary")

The emails use the reserved example.com domain. Seeding is idempotent: run it again to reset the demo
data (scripts/seed_firestore.py; local runs seed automatically). The accounts are protected: they can't be
deleted or renamed, and their sample listings can't be removed.
"""

from breedernear_core.accounts import hash_password

PASSWORD = "demo12345"
SELLER_ID, CUSTOMER_ID = "USR_DEFAULT_SELLER", "USR_DEFAULT_CUSTOMER"
SELLER_LOGIN, CUSTOMER_LOGIN = "karthik.seller@example.com", "priya.customer@example.com"
SELLER_BREEDER_ID = "BRD-CBE-001"                      # Karthik's Aviary in data/seed/breeders.json
CREATED = "2026-10-01T09:00:00+00:00"
DEFAULT_LOGINS = {"customer": CUSTOMER_LOGIN, "seller": SELLER_LOGIN}

# Sample listings of Karthik's Aviary: status and views shown on the seller dashboard.
LISTING_STATE = {
    "LST-0001": ("PUBLISHED", 24),
    "LST-0002": ("PUBLISHED", 31),
    "LST-0003": ("PAUSED", 12),
    "LST-0004": ("SOLD", 18),
}
# (enquiry id, listing, buyer, message, created)
ENQUIRIES = [
    ("ENQ_DEMO_1", "LST-0002", CUSTOMER_ID,
     "Hello, are the lutino lovebirds still available? Can I visit on Saturday morning?",
     "2026-10-08T05:10:00+00:00"),
    ("ENQ_DEMO_2", "LST-0001", CUSTOMER_ID,
     "Is the budgie pair suitable for my 8-year-old daughter? We live in a flat in Tiruppur.",
     "2026-10-09T11:40:00+00:00"),
    ("ENQ_DEMO_3", "LST-0001", "USR_SAMPLE_BUYER_1",
     "Do you also sell a cage with the pair? Please share the price.", "2026-10-07T14:20:00+00:00"),
    ("ENQ_DEMO_4", "LST-0002", "USR_SAMPLE_BUYER_2",
     "Are the parents on site? I would like to see them before buying.", "2026-10-06T08:05:00+00:00"),
]
CART = [("PRD-CAGE-002", 1), ("PRD-FOOD-001", 1), ("PRD-PERCH-001", 1), ("PRD-FEED-001", 1)]


def default_users() -> list[dict]:
    seller = {
        "id": SELLER_ID, "role": "seller", "name": "Karthik", "login": SELLER_LOGIN, "login_type": "email",
        "password_hash": hash_password(PASSWORD), "district": "coimbatore", "device_id": None,
        "demo": True, "default": True, "created_at": CREATED,
        "farm": {"farm_name": "Karthik's Aviary", "seller_type": "home_breeder", "locality": "Saibaba Colony",
                 "species": ["budgerigar", "lovebird", "cockatiel"], "sawb_registration_no": None,
                 "verification": "not_required"},
    }
    customer = {
        "id": CUSTOMER_ID, "role": "customer", "name": "Priya", "login": CUSTOMER_LOGIN,
        "login_type": "email",
        "password_hash": hash_password(PASSWORD), "district": "tiruppur", "device_id": None,
        "demo": True, "default": True, "created_at": CREATED,
    }
    return [seller, customer]


def seed_default_accounts(store) -> None:
    """Create or reset both accounts and their data. Sample listings must already be in the store."""
    for user in default_users():
        store.release_login(user["login"])
        store.claim_login(user["login"], user["id"])
        store.save_user(user["id"], user)
    for listing_id, (status, views) in LISTING_STATE.items():
        listing = store.get_listing(listing_id)
        if listing and listing.get("breeder_id") == SELLER_BREEDER_ID:
            listing.update(owner_user_id=SELLER_ID, status=status, views=views)
            store.save_listing(listing_id, listing)
    for enquiry_id, listing_id, buyer, message, created in ENQUIRIES:
        store.save_enquiry(enquiry_id, {
            "id": enquiry_id, "listing_id": listing_id, "breeder_id": SELLER_BREEDER_ID,
            "listing_owner_user_id": SELLER_ID, "buyer_user_id": buyer, "message": message,
            "demo": True, "created_at": created})
    store.save_cart(CUSTOMER_ID, {"items": [{"product_id": p, "quantity": q} for p, q in CART],
                                  "updated_at": CREATED})
