"""Fair-price checks against sample market ranges (data/seed/price_ranges.json)."""

from breedernear_core.data import load_seed, normalize
from breedernear_core.schemas import Check


def price_range(species_key: str | None, variety: str | None = None) -> tuple[int, int] | None:
    if not species_key:
        return None
    for entry in load_seed("price_ranges.json")["ranges"]:
        if entry["species_key"] == species_key:
            varieties = entry["varieties"]
            if variety:
                wanted = normalize(variety).strip().replace(" ", "_")
                if wanted in varieties:
                    return tuple(varieties[wanted])
            return tuple(varieties["default"])
    return None


def assess_price(price_inr: int | None, rng: tuple[int, int] | None) -> Check:
    if price_inr is None:
        return Check(name="price", result="info", detail="No price given; ask the seller.")
    if rng is None:
        return Check(name="price", result="info", detail="No sample price range for this species yet.")
    low, high = rng
    span = f"₹{low:,}–₹{high:,} (sample market data)"
    if price_inr < 0.5 * low:
        return Check(name="price", result="warn", penalty=30,
                     detail=f"Price is far below the usual range {span}: a common scam sign.")
    if price_inr < low:
        return Check(name="price", result="warn", penalty=10,
                     detail=f"Price is below the usual range {span}.")
    if price_inr > 1.5 * high:
        return Check(name="price", result="info", penalty=5,
                     detail=f"Price is well above the usual range {span}: compare before buying.")
    return Check(name="price", result="pass", detail=f"Price is within the usual range {span}.")
