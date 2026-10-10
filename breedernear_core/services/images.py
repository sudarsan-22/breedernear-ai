"""Perceptual (difference) hashing to detect reused listing photos."""

import io

from PIL import Image, ImageOps

DUPLICATE_MAX_DISTANCE = 6


def dhash(image_bytes: bytes, size: int = 8) -> str:
    """64-bit difference hash as 16 hex chars. Robust to resizing and recompression."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        gray = ImageOps.exif_transpose(img).convert("L").resize((size + 1, size), Image.LANCZOS)
        px = list(gray.get_flattened_data())
    bits = 0
    for row in range(size):
        for col in range(size):
            left, right = px[row * (size + 1) + col], px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:016x}"


def hamming(hash_a: str, hash_b: str) -> int:
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()


def find_duplicate(new_hash: str, known: dict[str, str]) -> str | None:
    """Return the listing ID whose photo hash is within DUPLICATE_MAX_DISTANCE, if any."""
    for listing_id, other in known.items():
        if hamming(new_hash, other) <= DUPLICATE_MAX_DISTANCE:
            return listing_id
    return None
