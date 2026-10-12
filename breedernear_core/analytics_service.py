"""Seller analytics (F14): events on a seller's listings, turned into chart series for the dashboard.

Events: "view" (a buyer opened the listing), "enquiry", "visit" (visit requested) and "sale" (buyer marked
"I bought this pet"; the amount is the listing price, paid in person, never through the app).
"""

import uuid
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta

from breedernear_core import deps

COLLECTION = "events"
TYPES = ("view", "enquiry", "visit", "sale")
WEEKS = 8


def record(seller_id: str | None, listing: dict, kind: str, amount_inr: int = 0,
           when: datetime | None = None) -> None:
    """Log one event for the listing's seller. Sample listings without an owner are not tracked."""
    if not seller_id or kind not in TYPES:
        return
    event_id = f"EVT_{uuid.uuid4().hex[:12]}"
    deps.get_store().put(COLLECTION, event_id, {
        "id": event_id, "seller_id": seller_id, "listing_id": listing.get("id"), "type": kind,
        "species": (listing.get("draft") or {}).get("species_common") or "Other",
        "amount_inr": int(amount_inr),
        "at": (when or datetime.now(UTC)).isoformat()})


def summary(seller_id: str, today: date | None = None) -> dict:
    """Charts in 8 rolling 7-day buckets ending today (oldest first), so a new week never starts empty."""
    today = today or datetime.now(UTC).date()
    weeks = [today - timedelta(days=7 * (WEEKS - 1 - i) + 6) for i in range(WEEKS)]  # each bucket's first day
    counts = [Counter() for _ in weeks]
    revenue = [0] * WEEKS
    by_species: defaultdict[str, int] = defaultdict(int)
    totals = Counter()
    sample = False
    for ev in deps.get_store().find(COLLECTION, seller_id=seller_id):
        sample = sample or bool(ev.get("sample"))
        back = (today - datetime.fromisoformat(ev["at"]).date()).days // 7
        if not 0 <= back < WEEKS:
            continue
        i = WEEKS - 1 - back
        counts[i][ev["type"]] += 1
        totals[ev["type"]] += 1
        if ev["type"] == "sale":
            revenue[i] += ev["amount_inr"]
            by_species[ev["species"]] += ev["amount_inr"]
    labels = [w.strftime("%d %b") for w in weeks]
    funnel = [{"stage": name, "count": totals[key]} for key, name in
              (("view", "Views"), ("enquiry", "Enquiries"), ("visit", "Visit requests"), ("sale", "Sales"))]
    rate = round(100 * totals["enquiry"] / totals["view"], 1) if totals["view"] else 0.0
    return {
        "status": "ok", "weeks": labels,
        "activity": {key: [c[key] for c in counts] for key in TYPES},
        "revenue_inr": revenue,
        "funnel": funnel,
        "revenue_by_species": sorted(({"species": k, "amount_inr": v} for k, v in by_species.items()),
                                     key=lambda r: -r["amount_inr"]),
        "totals": {"views": totals["view"], "enquiries": totals["enquiry"], "visits": totals["visit"],
                   "sales": totals["sale"], "revenue_inr": sum(revenue), "enquiry_rate_pct": rate},
        "sample_history": sample,
        "note": "Sales are what buyers marked as bought; payment happens in person, never in the app.",
    }
