"""Measure the Gemini photo screening against a labelled test set; writes evals/VISION_RESULTS.md.

Usage:
    GOOGLE_CLOUD_PROJECT=<id> GOOGLE_CLOUD_LOCATION=global GOOGLE_GENAI_USE_VERTEXAI=True \
        PYTHONPATH=. python scripts/vision_accuracy.py

Two sets:
- domestic: every sample listing photo (web/img/listings/), labelled with its listing's species. These
  must be named correctly and must NOT be flagged as protected, dyed, stock or poor.
- hard: data/samples/vision/cases.json (protected native species, a dyed bird, blurry, no animal,
  watermark, scam screenshot), each scored only on what it tests.

The protected decision uses the app's own rule (safety.trust_score.photo_shows_protected), so the
numbers describe what the trust check would do with the photo alone, without the seller's text.
"""

import datetime
import io
import json
import time
from pathlib import Path

from PIL import Image

from breedernear_core.config import get_settings
from breedernear_core.data import load_seed
from breedernear_core.safety.trust_score import photo_shows_protected
from breedernear_core.schemas import PhotoScreen

ROOT = Path(__file__).resolve().parent.parent
HARD = ROOT / "data" / "samples" / "vision"
OUT = ROOT / "evals" / "VISION_RESULTS.md"

# Words an answer must contain to count as the right species (group level for lovebird varieties).
SPECIES_WORDS = {
    "budgerigar": ["budg"],
    "lovebird": ["lovebird"],
    "fischer's lovebird": ["lovebird"],
    "cockatiel": ["cockatiel"],
    "zebra finch": ["zebra finch"],
    "society finch": ["society finch", "bengalese"],
    "canary": ["canary"],
    "labrador retriever": ["labrador"],
    "beagle": ["beagle"],
    "shih tzu": ["shih tzu", "shih-tzu"],
    "persian cat": ["persian"],
}


def domestic_cases() -> list[dict]:
    seen, cases = set(), []
    for item in load_seed("listings.json")["listings"]:
        photo = item.get("photo")
        if not photo or photo in seen:
            continue
        seen.add(photo)
        cases.append({"id": Path(photo).stem, "group": "domestic", "path": ROOT / "web" / photo,
                      "label": item["species_common"],
                      "expect": {"species_any": SPECIES_WORDS[item["species_common"].lower()],
                                 "protected": False, "dye": False, "stock": False, "quality": "good"}})
    return cases


def hard_cases() -> list[dict]:
    cases = json.loads((HARD / "cases.json").read_text())["cases"]
    return [{**c, "path": HARD / f"{c['id']}.webp", "label": c["id"].split("-", 1)[1].replace("-", " ")}
            for c in cases if (HARD / f"{c['id']}.webp").exists()]


def score(expect: dict, photo: PhotoScreen) -> dict[str, bool]:
    """One pass/fail per expectation the case declares."""
    results = {}
    if "species_any" in expect:
        guess = photo.species_guess.lower()
        results["species"] = any(word in guess for word in expect["species_any"])
    if "protected" in expect:
        results["protected"] = photo_shows_protected(photo) == expect["protected"]
    if "dye" in expect:
        results["dye"] = photo.possible_dye_or_disguise == expect["dye"]
    if "stock" in expect:
        results["stock"] = photo.looks_like_stock_or_watermarked == expect["stock"]
    if "quality" in expect:
        results["quality"] = photo.image_quality == expect["quality"]
    return results


def as_jpeg(path: Path) -> bytes:
    """The web app uploads JPEGs (shrunk in the browser), so test with the same format."""
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "JPEG", quality=88)
    return buf.getvalue()


def screen(vision, path: Path) -> PhotoScreen:
    for attempt in range(4):
        try:
            return vision.screen_photos([(as_jpeg(path), "image/jpeg")])
        except Exception as e:  # noqa: BLE001 - retry transient API errors
            print(f"  retry {attempt + 1}: {str(e)[:80]}", flush=True)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"screening failed for {path.name}")


def rate(rows: list[dict], group: str | None, check: str) -> tuple[int, int]:
    hits = [r["score"][check] for r in rows if (group is None or r["group"] == group) and check in r["score"]]
    return sum(hits), len(hits)


def report(rows: list[dict], model: str) -> str:
    def line(text: str, group: str | None, check: str) -> str:
        ok, n = rate(rows, group, check)
        return f"| {text} | **{ok}/{n}** |" if n else ""

    prot = [r for r in rows if r["group"] == "protected"]
    caught = sum(r["score"]["protected"] for r in prot)
    dom = [r for r in rows if r["group"] == "domestic"]
    false_alarm = sum(not r["score"]["protected"] for r in dom)
    all_checks = [ok for r in rows for ok in r["score"].values()]
    summary = "\n".join(x for x in [
        f"| Protected native species blocked from the photo alone | **{caught}/{len(prot)}** |",
        f"| Domestic pets wrongly flagged as protected | **{false_alarm}/{len(dom)}** |",
        line("Domestic species named correctly", "domestic", "species"),
        line("Domestic photos with no false dye flag", "domestic", "dye"),
        line("Domestic photos with no false stock/watermark flag", "domestic", "stock"),
        line("Dyed bird detected", "protected", "dye"),
        line("Blurry / no-animal photo recognised", "quality", "quality"),
        line("Watermarked stock photo / scam screenshot flagged", "stock", "stock"),
    ] if x)
    detail = "\n".join(
        f"| {r['id']} | {r['group']} | {r['label']} | {r['photo'].species_guess} "
        f"({r['photo'].species_guess_confidence:.2f}) | "
        + " ".join(f"{'✅' if ok else '❌'} {name}" for name, ok in r["score"].items()) + " |"
        for r in rows)
    return (
        "# Photo screening accuracy\n\n"
        f"Run on {datetime.date.today().isoformat()} with `{model}`: "
        f"**{sum(all_checks)}/{len(all_checks)} checks correct** across {len(rows)} photos.\n\n"
        "Reproduce with `PYTHONPATH=. python scripts/vision_accuracy.py` (needs Google Cloud credentials). "
        "The protected result uses the app's own rule on the photo alone; in the app the seller's text is "
        "checked too, and either one is enough to block.\n\n"
        "**Limits:** every test photo is AI-generated (sample listing photos, plus the hard cases in "
        "`data/samples/vision/`), so accuracy on real phone photos may be lower. Real photos taken with "
        "consent can be added to `cases.json`.\n\n"
        "**Tuning:** the first run (10 Oct) scored 196/202. Two prompt fixes followed: \"stock photo\" now "
        "needs visible evidence (5 polished pet photos had been flagged, which would cost honest sellers "
        "trust points), and dog and cat breeds are named. Because the prompt was tuned on this set, treat "
        "the result as an upper bound until it is checked on new photos.\n\n"
        f"| Measure | Result |\n|---|---|\n{summary}\n\n"
        "## Every photo\n\n| Photo | Set | Label | Gemini's guess (confidence) | Checks |\n"
        "|---|---|---|---|---|\n"
        f"{detail}\n"
    )


def main() -> None:
    from breedernear_core.services.vision import GeminiVision

    model = get_settings().breedernear_model
    vision = GeminiVision(model)
    rows = []
    for case in domestic_cases() + hard_cases():
        photo = screen(vision, case["path"])
        rows.append({**case, "photo": photo, "score": score(case["expect"], photo)})
        marks = " ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in rows[-1]["score"].items())
        guess = f"{photo.species_guess} ({photo.species_guess_confidence:.2f})"
        print(f"{case['id']}: {guess} {marks}", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(report(rows, model))
    print(OUT.read_text().split("\n\n")[1])


if __name__ == "__main__":
    main()
