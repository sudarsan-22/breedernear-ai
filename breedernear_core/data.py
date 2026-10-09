import json
import re
from functools import lru_cache
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"


@lru_cache
def load_seed(name: str) -> dict:
    """Load a JSON file from data/seed (cached; seed files are read-only at runtime)."""
    with open(SEED_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    """Lowercase, turn punctuation into spaces and pad with spaces for whole-phrase matching."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower().replace("'", ""))
    return f" {cleaned.strip()} "


def contains_phrase(normalized_text: str, phrase: str) -> bool:
    return normalize(phrase) in normalized_text
