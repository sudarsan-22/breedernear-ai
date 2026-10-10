import io

import pytest
from PIL import Image, ImageDraw

from breedernear_core import deps
from breedernear_core.schemas import CarePlan, EnquiryReply, ListingDraft, Phase, PhotoScreen
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
        self.plan = CarePlan(
            species="Budgerigar", diet=["Seed mix with fresh greens", "Never avocado or chocolate"],
            daily_routine=["Fresh water every morning"],
            phases=[Phase(title="Days 0-2: Settling in", steps=["Keep the cage in a quiet, shaded room"]),
                    Phase(title="Days 3-7: Building routine", steps=["Talk softly near the cage"]),
                    Phase(title="Days 8-14: Bonding and checks", steps=["Offer millet from your hand"])],
            see_vet_if=["Fluffed up for hours", "Not eating for a day", "Breathing with tail bobbing"])
        self.care_calls: list[str] = []
        self.reply = EnquiryReply(reply="Yes, the pair is available. You are welcome to visit on Saturday.",
                                  needs_seller_input=["visit times"])
        self.reply_calls: list[str] = []

    def extract_listing(self, text, images):
        self.extract_calls.append((text, len(images)))
        return self.draft

    def screen_photos(self, images):
        return self.photo

    def write_care_plan(self, facts):
        self.care_calls.append(facts)
        return self.plan

    def write_reply(self, facts):
        self.reply_calls.append(facts)
        return self.reply


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


@pytest.fixture
def seeded(fakes):
    """The fakes, with the curated sample listings loaded into the store."""
    from breedernear_core.catalog import seed_listings
    store = fakes[0]
    for listing in seed_listings():
        store.save_listing(listing["id"], listing)
    return fakes


@pytest.fixture(autouse=True)
def reset_rate_limit():
    from app.ratelimit import limiter
    limiter.reset()
    yield
    limiter.reset()


DEVICE = "3f2b9c1e-7a4d-4e8b-9c0a-1234567890ab"


def auth_headers(client, role: str, device: str = DEVICE) -> dict:
    """Sign in with a fresh demo account and return the Authorization header."""
    r = client.post("/api/auth/demo", json={"role": role}, headers={"X-Device-Id": device})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
