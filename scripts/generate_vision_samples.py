"""Generate the hard cases for the photo-screening accuracy test (scripts/vision_accuracy.py).

Usage:
    GOOGLE_CLOUD_PROJECT=<id> GOOGLE_CLOUD_LOCATION=global GOOGLE_GENAI_USE_VERTEXAI=True \
        PYTHONPATH=. python scripts/generate_vision_samples.py [case-id ...]

The easy cases are the sample listing photos in web/img/listings/. These are the cases a trust check
must get right: protected native species, a dyed bird, a blurry photo, no animal, a watermarked stock
photo and a scam post screenshot. Saved as 800x600 WebP in data/samples/vision/ (not served by the app)
and listed in ATTRIBUTIONS.md.
"""

import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.generate_sample_images import PAUSE_SECONDS, generate, save_webp

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "samples" / "vision"
REAL = ("A realistic, natural smartphone photo taken in Tamil Nadu, India. No people, no hands, "
        "no text, no watermark, no logos, no frames.")


def cases() -> list[dict]:
    return json.loads((OUT / "cases.json").read_text())["cases"]


def prompts() -> dict[str, str]:
    return {c["id"]: c["prompt"].replace("{REAL}", REAL) for c in cases() if c.get("prompt")}


def watermark(source: Path, target: Path, text: str = "STOCK PREVIEW") -> None:
    """Stamp a repeated diagonal watermark on a photo, like a stock image copied into a sale post."""
    img = Image.open(source).convert("RGBA")
    layer = Image.new("RGBA", (img.width * 2, img.height * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.load_default(size=44)
    for y in range(0, layer.height, 120):
        for x in range(-200 + (y // 120) % 2 * 160, layer.width, 420):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 120), stroke_width=2,
                      stroke_fill=(0, 0, 0, 60))
    layer = layer.rotate(30, center=(layer.width // 2, layer.height // 2))
    left, top = (layer.width - img.width) // 2, (layer.height - img.height) // 2
    img.alpha_composite(layer.crop((left, top, left + img.width, top + img.height)))
    img.convert("RGB").save(target, "WEBP", quality=80, method=6)


def main(only: list[str]) -> None:
    from google import genai

    for case in cases():
        target = OUT / f"{case['id']}.webp"
        if case.get("source") and (not target.exists() or case["id"] in only):
            watermark(ROOT / case["source"], target)
    client = genai.Client()
    for case_id, prompt in prompts().items():
        target = OUT / f"{case_id}.webp"
        if (only and case_id not in only) or (target.exists() and not only):
            continue
        print(f"{case_id}: {prompt[:100]}…", flush=True)
        save_webp(generate(client, prompt), target)
        time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main(sys.argv[1:])
