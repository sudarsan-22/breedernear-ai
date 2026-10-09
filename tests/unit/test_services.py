import io
from datetime import date

import pytest
from PIL import Image, ImageDraw

from breedernear_core.services.geo import distance_km, resolve_district
from breedernear_core.services.images import dhash, find_duplicate, hamming
from breedernear_core.services.registry import sawb_status


def _image(seed: int, size=(400, 300), fmt="PNG", quality=95) -> bytes:
    img = Image.new("RGB", size, (240, 240, 240))
    d = ImageDraw.Draw(img)
    for i in range(12):
        x = (seed * 37 + i * 53) % size[0]
        y = (seed * 91 + i * 29) % size[1]
        d.ellipse([x, y, x + 60, y + 40], fill=((seed * 50 + i * 20) % 255, 80, (i * 40) % 255))
    buf = io.BytesIO()
    img.save(buf, format=fmt, **({"quality": quality} if fmt == "JPEG" else {}))
    return buf.getvalue()


def test_same_photo_resized_and_recompressed_is_a_duplicate():
    original = _image(1)
    with Image.open(io.BytesIO(original)) as img:
        buf = io.BytesIO()
        img.resize((200, 150)).save(buf, format="JPEG", quality=60)
    assert hamming(dhash(original), dhash(buf.getvalue())) <= 6


def test_different_photos_are_not_duplicates():
    assert hamming(dhash(_image(1)), dhash(_image(7))) > 6


def test_find_duplicate_returns_matching_listing():
    h = dhash(_image(3))
    assert find_duplicate(h, {"LST-1": dhash(_image(9)), "LST-2": h}) == "LST-2"
    assert find_duplicate(h, {"LST-1": dhash(_image(9))}) is None


@pytest.mark.parametrize("name,key", [
    ("Coimbatore", "coimbatore"), ("kovai", "coimbatore"), ("Tirupur", "tiruppur"),
    ("Bangalore", "bengaluru"), ("Trichy", "tiruchirappalli"), ("Atlantis", None), (None, None),
])
def test_resolve_district(name, key):
    assert resolve_district(name) == key


def test_coimbatore_to_tiruppur_is_about_45_km():
    assert 35 <= distance_km("coimbatore", "tiruppur") <= 55


def test_unknown_district_distance_raises():
    with pytest.raises(KeyError):
        distance_km("coimbatore", "atlantis")


def test_sawb_registry_statuses():
    today = date(2026, 10, 10)
    assert sawb_status("SIM-TNAWB-DB-0042", today) == "valid"
    assert sawb_status("sim-tnawb-db-0042 ", today) == "valid"
    assert sawb_status("SIM-TNAWB-DB-0001", today) == "expired"
    assert sawb_status("TN/123/REAL", today) == "unknown"
    assert sawb_status("", today) == "missing"
    assert sawb_status(None, today) == "missing"
