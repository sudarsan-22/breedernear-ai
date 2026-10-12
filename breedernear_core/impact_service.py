"""Impact so far: what the trust checks have stopped, counted from the platform's own data.

Listings, enquiries and breeders are counted live. Posts checked from outside (WhatsApp, Instagram, Facebook)
are never stored, so only three counters are kept for them: checked, flagged and protected species found.
"""

from breedernear_core import deps

COLLECTION = "impact"
DOC = "posts"
COUNTERS = ("posts_checked", "posts_flagged", "posts_protected")


def record_post_check(screening: dict) -> None:
    """Count one outside post. Nothing about the post itself is kept."""
    checks = screening.get("checks") or []
    protected = any(c.get("result") == "block" for c in checks)
    flagged = screening.get("trust_level") != "TRUSTED"
    store = deps.get_store()
    counts = store.fetch(COLLECTION, DOC) or dict.fromkeys(COUNTERS, 0)
    counts["posts_checked"] = counts.get("posts_checked", 0) + 1
    counts["posts_flagged"] = counts.get("posts_flagged", 0) + int(flagged)
    counts["posts_protected"] = counts.get("posts_protected", 0) + int(protected)
    store.put(COLLECTION, DOC, counts)


def summary(guest_id: str) -> dict:
    from breedernear_core import directory_service  # here: directory imports the listing modules

    store = deps.get_store()
    listings = store.all_listings()
    messages = [e.get("scan") for e in store.all_enquiries()]
    messages += [(e.get("reply") or {}).get("scan") for e in store.all_enquiries()]
    breeders = directory_service.list_breeders(guest_id)["breeders"]
    posts = store.fetch(COLLECTION, DOC) or {}
    return {
        "status": "ok",
        "listings_screened": len(listings),
        "listings_blocked": sum(x.get("status") == "BLOCKED" for x in listings),
        "listings_caution": sum(x.get("trust_level") == "CAUTION" for x in listings),
        "posts_checked": posts.get("posts_checked", 0),
        "posts_flagged": posts.get("posts_flagged", 0),
        "posts_protected": posts.get("posts_protected", 0),
        "messages_flagged": sum(1 for m in messages if m and m.get("risk") not in (None, "none")),
        "verified_breeders": sum(bool(b.get("verified_breeder")) for b in breeders),
        "registered_dog_breeders": sum(b.get("dog_registration") == "valid" for b in breeders),
        "note": "Counted live from this prototype, including its sample listings and breeders. "
                "Outside posts are never stored; only the counts are kept.",
    }
