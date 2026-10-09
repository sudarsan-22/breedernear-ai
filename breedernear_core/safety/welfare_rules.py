"""Animal-welfare rules for starter kits, e.g. minimum cage size per species and count."""

import math

from breedernear_core.data import load_seed


def min_cage_cm(species_key: str, count: int) -> tuple[int, int, int] | None:
    """Minimum cage (width, depth, height) in cm. Each extra pair adds 50% width."""
    for sp in load_seed("species.json")["species"]:
        if sp["key"] == species_key and "min_cage_cm_per_pair" in sp:
            width, depth, height = sp["min_cage_cm_per_pair"]
            pairs = max(1, math.ceil(count / 2))
            return (math.ceil(width * (1 + 0.5 * (pairs - 1))), depth, height)
    return None


def cage_is_big_enough(cage_cm: tuple[int, int, int], species_key: str, count: int) -> bool:
    required = min_cage_cm(species_key, count)
    if required is None:
        return True
    return all(have >= need for have, need in zip(cage_cm, required, strict=True))
