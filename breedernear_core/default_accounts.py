"""Two permanent demo accounts with preloaded data, so judges see a lived-in app.

    Customer: priya.customer@example.com / demo12345
    Seller:   karthik.seller@example.com / demo12345   (owns the sample breeder "Karthik's Aviary")

The emails use the reserved example.com domain. Seeding is idempotent: run it again to reset the demo
data (scripts/seed_firestore.py; local runs seed automatically). The accounts are protected: they can't be
deleted or renamed, and their sample listings can't be removed.
"""

import random
from datetime import UTC, datetime, timedelta

from breedernear_core.accounts import hash_password

PASSWORD = "demo12345"
SELLER_ID, CUSTOMER_ID = "USR_DEFAULT_SELLER", "USR_DEFAULT_CUSTOMER"
SELLER_LOGIN, CUSTOMER_LOGIN = "karthik.seller@example.com", "priya.customer@example.com"
SELLER_BREEDER_ID = "BRD-CBE-001"  # Karthik's Aviary in data/seed/breeders.json
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
    (
        "ENQ_DEMO_1",
        "LST-0002",
        CUSTOMER_ID,
        "Hello, are the lutino lovebirds still available? Can I visit on Saturday morning?",
        "2026-10-08T05:10:00+00:00",
    ),
    (
        "ENQ_DEMO_2",
        "LST-0001",
        CUSTOMER_ID,
        "Is the budgie pair suitable for my 8-year-old daughter? We live in a flat in Tiruppur.",
        "2026-10-09T11:40:00+00:00",
    ),
    (
        "ENQ_DEMO_3",
        "LST-0001",
        "USR_SAMPLE_BUYER_1",
        "Do you also sell a cage with the pair? Please share the price.",
        "2026-10-07T14:20:00+00:00",
    ),
    (
        "ENQ_DEMO_4",
        "LST-0002",
        "USR_SAMPLE_BUYER_2",
        "Are the parents on site? I would like to see them before buying.",
        "2026-10-06T08:05:00+00:00",
    ),
]
CART = [("PRD-CAGE-002", 1), ("PRD-FOOD-001", 1), ("PRD-PERCH-001", 1), ("PRD-FEED-001", 1)]


def default_users() -> list[dict]:
    seller = {
        "id": SELLER_ID,
        "role": "seller",
        "name": "Karthik",
        "login": SELLER_LOGIN,
        "login_type": "email",
        "password_hash": hash_password(PASSWORD),
        "district": "coimbatore",
        "device_id": None,
        "demo": True,
        "default": True,
        "created_at": CREATED,
        "verification_status": "verified",
        "farm": {
            "farm_name": "Karthik's Aviary",
            "seller_type": "home_breeder",
            "locality": "Saibaba Colony",
            "species": ["budgerigar", "lovebird", "cockatiel"],
            "sawb_registration_no": None,
            "verification": "not_required",
        },
    }
    customer = {
        "id": CUSTOMER_ID,
        "role": "customer",
        "name": "Priya",
        "login": CUSTOMER_LOGIN,
        "login_type": "email",
        "password_hash": hash_password(PASSWORD),
        "district": "tiruppur",
        "device_id": None,
        "demo": True,
        "default": True,
        "created_at": CREATED,
    }
    return [seller, customer]


def seed_default_accounts(store) -> None:
    """Create or reset both accounts and their data. Sample listings must already be in the store.

    Anything visitors added to these shared accounts is removed: listings the demo seller published and
    enquiries sent by or to them (other than the preloaded ones).
    """
    for listing in store.all_listings():
        if listing.get("owner_user_id") == SELLER_ID and not listing.get("simulated"):
            store.delete_listing(listing["id"])
    preloaded = {e[0] for e in ENQUIRIES}
    for enquiry in store.all_enquiries():
        ours = (
            SELLER_ID in (enquiry.get("listing_owner_user_id"), enquiry.get("buyer_user_id"))
            or enquiry.get("buyer_user_id") == CUSTOMER_ID
        )
        if ours and enquiry.get("id") not in preloaded:
            store.delete_enquiry(enquiry["id"])
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
        store.save_enquiry(
            enquiry_id,
            {
                "id": enquiry_id,
                "listing_id": listing_id,
                "breeder_id": SELLER_BREEDER_ID,
                "listing_owner_user_id": SELLER_ID,
                "buyer_user_id": buyer,
                "message": message,
                "demo": True,
                "created_at": created,
            },
        )
    store.save_cart(
        CUSTOMER_ID, {"items": [{"product_id": p, "quantity": q} for p, q in CART], "updated_at": CREATED}
    )
    seed_seller_extras(store)
    seed_customer_extras(store)


def seed_seller_extras(store, today: datetime | None = None) -> None:
    """The demo seller's verified status and 8 weeks of SAMPLE analytics (labelled as sample in the app)."""
    now = today or datetime.now(UTC)
    for ev in store.find("events", seller_id=SELLER_ID):
        store.remove("events", ev["id"])
    rng = random.Random(2026)
    listings = [store.get_listing(lid) for lid in LISTING_STATE]
    listings = [lst for lst in listings if lst]
    n = 0
    for week in range(8, 0, -1):
        start = now - timedelta(weeks=week)
        views = rng.randint(14, 34) + (8 - week) * 2  # a gently growing farm
        plan = [
            ("view", views),
            ("enquiry", max(1, views // rng.randint(6, 9))),
            ("visit", max(0, views // rng.randint(12, 18))),
            ("sale", max(0, views // rng.randint(22, 34))),
        ]
        for kind, count in plan:
            for _ in range(count):
                lst = rng.choice(listings)
                n += 1
                store.put(
                    "events",
                    f"EVT_DEMO_{n:04d}",
                    {
                        "id": f"EVT_DEMO_{n:04d}",
                        "seller_id": SELLER_ID,
                        "listing_id": lst["id"],
                        "type": kind,
                        "species": lst["draft"]["species_common"],
                        "sample": True,
                        "amount_inr": lst.get("price_inr", 0) if kind == "sale" else 0,
                        "at": (
                            start + timedelta(days=rng.randint(0, 6), hours=rng.randint(8, 19))
                        ).isoformat(),
                    },
                )
    for lst in listings:  # dashboard tiles agree with the charts
        lst["views"] = sum(
            1
            for ev in store.find("events", seller_id=SELLER_ID, listing_id=lst["id"])
            if ev["type"] == "view"
        )
        store.save_listing(lst["id"], lst)
    layer = {"updated_at": now.isoformat()}
    store.put(
        "verifications",
        SELLER_ID,
        {
            "user_id": SELLER_ID,
            "status": "verified",
            "open_items": [],
            "updated_at": now.isoformat(),
            "phone": {
                **layer,
                "status": "pass",
                "reason": "Mobile number confirmed.",
                "masked": "+91•••••••210",
            },
            "facility": {
                **layer,
                "status": "pass",
                "reason": "Facility photos show clean, roomy housing.",
                "observations": ["spacious flight cages", "fresh water and seed", "natural perches"],
            },
            "certificate": {
                **layer,
                "status": "not_required",
                "reason": "Only dog breeders need a registration certificate.",
            },
            "sample": True,
        },
    )


def seed_customer_extras(store, today: datetime | None = None) -> None:
    """Priya's profile, her pet Mango (bought after a visit) with logs and weights, and a visit request
    waiting for Karthik. Everything the two demo accounts did before is removed first."""
    now = today or datetime.now(UTC)
    for collection, field in (
        ("pets", "owner_id"),
        ("pet_logs", "owner_id"),
        ("pet_weights", "owner_id"),
        ("visits", "buyer_id"),
        ("sales", "buyer_id"),
    ):
        for rec in store.find(collection, **{field: CUSTOMER_ID}):
            store.remove(collection, rec["id"])
    for rec in store.find("visits", seller_id=SELLER_ID) + store.find("sales", seller_id=SELLER_ID):
        store.remove("visits" if rec["id"].startswith("VIS") else "sales", rec["id"])
    store.put(
        "buyer_profiles",
        CUSTOMER_ID,
        {
            "user_id": CUSTOMER_ID,
            "updated_at": now.isoformat(),
            "words": "We live in a 2BHK flat in Tiruppur with our 8-year-old daughter. First pet. "
            "Budget about 3000.",
            "profile": {
                "animal_group": "bird",
                "home_type": "flat",
                "has_young_children": True,
                "first_time_owner": True,
                "time_per_day_minutes": 45,
                "hours_away_per_day": 8,
                "noise_ok": True,
                "activity": "medium",
                "allergies": False,
                "budget_inr": 3000,
                "district": "tiruppur",
            },
        },
    )
    home = (now - timedelta(days=6)).date()
    store.put(
        "visits",
        "VIS_DEMO_MANGO",
        {
            "id": "VIS_DEMO_MANGO",
            "listing_id": "LST-0009",
            "buyer_id": CUSTOMER_ID,
            "seller_id": None,
            "species": "Budgerigar",
            "breeder": "Noyyal Finch House",
            "date": (home - timedelta(days=1)).isoformat(),
            "slot": "morning",
            "slot_label": "Morning (9–12)",
            "note": "",
            "status": "confirmed",
            "sample_breeder": True,
            "created_at": (now - timedelta(days=9)).isoformat(),
            "purchased": True,
            "pet_id": "PET_DEMO_MANGO",
        },
    )
    store.put(
        "pets",
        "PET_DEMO_MANGO",
        {
            "id": "PET_DEMO_MANGO",
            "owner_id": CUSTOMER_ID,
            "name": "Mango",
            "species_key": "budgerigar",
            "species": "Budgerigar",
            "variety": "Blue",
            "group": "bird",
            "age_months_at_home": 3,
            "home_date": home.isoformat(),
            "listing_id": "LST-0009",
            "sale_id": None,
            "sample": True,
            "created_at": (now - timedelta(days=6)).isoformat(),
        },
    )
    logs = [
        ("Seed mix and a little coriander", "Explored the new perches", "Shy on the first day", True),
        ("Seed mix, millet spray", "Chirped back when we talked", "", True),
        ("Seed mix, cucumber slice", "Climbed the ladder", "", True),
        ("Seed mix and spinach", "Flew short hops in the cage", "Ate well", True),
        ("Seed mix, apple (no seeds)", "Played with the bell", "", True),
    ]
    for i, (food, play, note, ok) in enumerate(logs):
        day = home + timedelta(days=i + 1)
        store.put(
            "pet_logs",
            f"LOG_DEMO_{i}",
            {
                "id": f"LOG_DEMO_{i}",
                "pet_id": "PET_DEMO_MANGO",
                "owner_id": CUSTOMER_ID,
                "day": day.isoformat(),
                "at": datetime(day.year, day.month, day.day, 19, tzinfo=UTC).isoformat(),
                "food": food,
                "play": play,
                "note": note,
                "had_photo": False,
                "food_ok": ok,
                "sample": True,
                "feedback": "A healthy mix for a young budgie.",
                "suggestions": ["Keep fresh water topped up."],
            },
        )
    for i, grams in enumerate((31, 32, 32)):
        day = home + timedelta(days=2 * i + 1)
        store.put(
            "pet_weights",
            f"WGT_DEMO_{i}",
            {
                "id": f"WGT_DEMO_{i}",
                "pet_id": "PET_DEMO_MANGO",
                "owner_id": CUSTOMER_ID,
                "value": grams,
                "unit": "g",
                "day": day.isoformat(),
                "at": datetime(day.year, day.month, day.day, 9, tzinfo=UTC).isoformat(),
            },
        )
    store.put(
        "visits",
        "VIS_DEMO_PENDING",
        {
            "id": "VIS_DEMO_PENDING",
            "listing_id": "LST-0002",
            "buyer_id": CUSTOMER_ID,
            "seller_id": SELLER_ID,
            "species": "Lovebird",
            "breeder": "Karthik's Aviary",
            "date": (now + timedelta(days=3)).date().isoformat(),
            "slot": "evening",
            "slot_label": "Evening (4–7)",
            "note": "Can we see the parents too?",
            "status": "requested",
            "sample_breeder": False,
            "created_at": now.isoformat(),
            "purchased": False,
        },
    )
