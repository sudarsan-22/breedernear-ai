import io

import pytest
from PIL import Image, ImageDraw

from breedernear_core import deps
from breedernear_core.schemas import ListingDraft, PhotoScreen
from breedernear_core.services.store import MemoryStore
from breedernear_core.services.uploads import MemoryUploads


class FakeVision:
    """Stands in for Gemini: returns whatever the test sets."""

    def __init__(self) -> None:
        self.draft = ListingDraft(
            species_common="Lovebird", variety="Lutino", animal_group="bird", count=4, unit="pair",
            price_inr=1800, district="Coimbatore", locality="Saibaba Colony",
            missing_fields=["health_notes"], confidence=0.9)
        self.photo = PhotoScreen(species_guess="Peach-faced lovebird", species_guess_confidence=0.9)
        self.extract_calls: list[tuple[str, int]] = []

    def extract_listing(self, text, images):
        self.extract_calls.append((text, len(images)))
        return self.draft

    def screen_photos(self, images):
        return self.photo


def make_image(seed: int) -> bytes:
    img = Image.new("RGB", (320, 240), (235, 235, 230))
    d = ImageDraw.Draw(img)
    for i in range(10):
        x, y = (seed * 41 + i * 57) % 320, (seed * 83 + i * 31) % 240
        d.ellipse([x, y, x + 50, y + 35], fill=((seed * 60 + i * 25) % 255, 90, (i * 45) % 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture
def fakes():
    store, uploads, vision = MemoryStore(), MemoryUploads(), FakeVision()
    deps.set_deps(store=store, uploads=uploads, vision=vision)
    yield store, uploads, vision
    deps.set_deps()
