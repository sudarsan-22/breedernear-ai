"""Generate the illustrative photos for the sample listings with a Google Gemini image model.

Usage:
    GOOGLE_CLOUD_PROJECT=<id> GOOGLE_CLOUD_LOCATION=global GOOGLE_GENAI_USE_VERTEXAI=True \
        PYTHONPATH=. python scripts/generate_sample_images.py [LST-0001 ...]

Each listing gets its own image (the trust check flags photos reused across listings), except the
deliberate "reused photo" demo case, which shares one file. BLOCKED (protected species) listings get
no photo. Images are saved as 800x600 WebP in web/img/listings/ and listed in ATTRIBUTIONS.md.
"""

import io
import sys
import time
from pathlib import Path

from PIL import Image

from breedernear_core.data import load_seed

MODEL = "gemini-3.1-flash-image"
PAUSE_SECONDS = 30          # the image model's per-minute quota is small on new projects
OUT = Path(__file__).resolve().parent.parent / "web"

LOOKS = {
    ("budgerigar", "mixed colours"): "budgerigars in green, blue and yellow",
    ("budgerigar", "blue"): "sky-blue budgerigars with black-and-white barred wings",
    ("budgerigar", "hand tamed"): "a calm, tame green budgerigar pair",
    ("budgerigar", ""): "green budgerigars",
    ("lovebird", "lutino"): "lutino peach-faced lovebirds: bright yellow bodies with red-orange faces",
    ("lovebird", "green (peach-faced)"): "peach-faced lovebirds with green bodies and rosy-peach faces",
    ("lovebird", "peach-faced"): "peach-faced lovebirds with green bodies and rosy-peach faces",
    ("lovebird", "albino"): "albino lovebirds: creamy-white bodies with pale peach faces and red eyes",
    ("lovebird", ""): "green peach-faced lovebirds",
    ("fischer's lovebird", ""): "Fischer's lovebirds: green bodies, orange-red faces and white eye rings",
    ("cockatiel", "grey"): "grey cockatiels with yellow faces, crests and orange cheek patches",
    ("cockatiel", "lutino"): "lutino cockatiels: creamy-yellow feathers with bright orange cheek patches",
    ("cockatiel", "pied"): "pied cockatiels with irregular grey and yellow patches",
    ("zebra finch", ""): "zebra finches with orange beaks, chestnut cheeks and striped chests",
    # Domestic pied colouring, so they can't be mistaken for protected wild munias.
    ("society finch", ""): ("domesticated society (Bengalese) finches with bold pied plumage: large "
                            "pure-white patches mixed with chocolate-brown, no scaly or speckled chest"),
    ("canary", "yellow"): "bright yellow canaries",
    ("canary", "red factor"): "red-factor canaries with orange-red feathers",
    ("labrador retriever", "yellow"): "yellow Labrador Retriever puppies",
    ("labrador retriever", "black"): "black Labrador Retriever puppies",
    ("labrador retriever", "golden"): "golden Labrador Retriever puppies",
    ("beagle", "tricolour"): "tricolour Beagle puppies",
    ("beagle", ""): "tricolour Beagle puppies",
    ("shih tzu", ""): "fluffy Shih Tzu puppies",
    ("persian cat", "white"): "white long-haired Persian kittens",
    ("persian cat", "doll face"): "a doll-face Persian kitten with a cream coat",
}
BIRD_SCENES = [
    "inside a clean, spacious powder-coated flight cage with natural wooden perches, on a shaded balcony",
    "perched on a natural wooden branch inside a bright home aviary with green plants behind",
    "in a tidy cage with seed and water cups, on a verandah with soft morning light",
    "on a wooden perch near a window, with a softly blurred terracotta-coloured wall behind",
]
DOG_SCENES = ["sitting on a clean cotton mat in a sunny home courtyard",
              "playing on fresh green grass in a home garden",
              "resting together on a clean blanket on a tiled verandah"]
CAT_SCENES = ["sitting on a soft blanket on a wooden bench indoors, gentle window light",
              "resting on a cushion in a bright, tidy living room"]
STYLE = ("A realistic, natural photo taken with a good smartphone by a home breeder in Tamil Nadu, India. "
         "Healthy, alert animals, clean surroundings, shallow depth of field, true-to-life colours. "
         "No people, no hands, no text, no watermark, no logos, no frames.")


def prompt_for(item: dict, index: int) -> str:
    species = item["species_common"].lower()
    variety = (item.get("variety") or "").lower()
    look = LOOKS.get((species, variety)) or LOOKS.get((species, "")) or item["species_common"]
    many = {"pair": "two", "single": "two" if item["count"] > 1 else "one"}.get(item["unit"], "two")
    if item["animal_group"] == "dog":
        scene = DOG_SCENES[index % len(DOG_SCENES)]
        subject = f"{many} {look}, about {item['age_months']} months old"
    elif item["animal_group"] == "cat":
        scene = CAT_SCENES[index % len(CAT_SCENES)]
        subject = f"{'two' if item['count'] > 1 else 'one'} {look}"
    else:
        scene, subject = BIRD_SCENES[index % len(BIRD_SCENES)], f"two {look}"
    return f"{subject}, {scene}. {STYLE}"


def generate(client, prompt: str) -> bytes:
    from google.genai import types

    for attempt in range(6):
        try:
            response = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"],
                                                   image_config=types.ImageConfig(aspect_ratio="4:3")))
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
        except Exception as e:  # noqa: BLE001 - retry transient API errors
            print(f"  retry {attempt + 1}: {str(e)[:80]}", flush=True)
            time.sleep(30 * (attempt + 1))
    raise RuntimeError("no image returned")


def save_webp(data: bytes, path: Path) -> None:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((800, 600))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=80, method=6)


def main(only: list[str]) -> None:
    from google import genai

    client = genai.Client()
    done: set[str] = set()
    for index, item in enumerate(load_seed("listings.json")["listings"]):
        photo = item.get("photo")
        if not photo or photo in done or (only and item["id"] not in only):
            continue
        target = OUT / photo
        if target.exists() and not only:
            print(f"{item['id']}: exists, skipped")
            done.add(photo)
            continue
        prompt = prompt_for(item, index)
        print(f"{item['id']}: {prompt[:110]}…", flush=True)
        save_webp(generate(client, prompt), target)
        done.add(photo)
        time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main(sys.argv[1:])
