"""District lookup and approximate distances (haversine between district centroids)."""

import math

from breedernear_core.data import load_seed, normalize

EARTH_RADIUS_KM = 6371.0


def resolve_district(name: str | None) -> str | None:
    if not name:
        return None
    data = load_seed("districts.json")
    key = normalize(name).strip()
    if key in data["aliases"]:
        return data["aliases"][key]
    for d in data["districts"]:
        if key in (d["key"], normalize(d["name"]).strip()):
            return d["key"]
    return None


def _coords(key: str) -> tuple[float, float]:
    for d in load_seed("districts.json")["districts"]:
        if d["key"] == key:
            return d["lat"], d["lng"]
    raise KeyError(f"Unknown district: {key}")


def distance_km(district_a: str, district_b: str) -> float:
    (lat1, lng1), (lat2, lng2) = _coords(district_a), _coords(district_b)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
