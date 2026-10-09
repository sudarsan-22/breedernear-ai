"""Protected native species and CITES species detection (rules R26, docs/product/03)."""

from dataclasses import dataclass

from breedernear_core.data import contains_phrase, load_seed, normalize


@dataclass(frozen=True)
class SpeciesMatch:
    key: str
    common_name: str
    matched: str


def _strip_lookalikes(text: str) -> str:
    """Remove allowed domestic/exotic names (e.g. 'society munia') before protected matching."""
    norm = normalize(text)
    for phrase in load_seed("protected_species.json")["allowed_lookalikes"]["phrases"]:
        norm = norm.replace(normalize(phrase), " ")
    return norm


def find_protected(*texts: str) -> list[SpeciesMatch]:
    """Return protected native species named in any of the texts (breeder text, model guess…)."""
    data = load_seed("protected_species.json")
    matches: dict[str, SpeciesMatch] = {}
    for text in texts:
        if not text:
            continue
        norm = _strip_lookalikes(text)
        for sp in data["species"]:
            for alias in sp["aliases"]:
                if contains_phrase(norm, alias):
                    matches.setdefault(sp["key"], SpeciesMatch(sp["key"], sp["common_name"], alias))
                    break
        generic = data["generic_terms"]
        if not any(contains_phrase(norm, a) for a in generic["allowed_if_also_mentions"]):
            for term in generic["terms"]:
                if contains_phrase(norm, term):
                    matches.setdefault(
                        "generic_native_parrot",
                        SpeciesMatch("generic_native_parrot", "Native Indian parakeet", term),
                    )
                    break
    return list(matches.values())


def find_cites(*texts: str) -> list[SpeciesMatch]:
    """Return CITES-listed exotic species named in any of the texts."""
    data = load_seed("cites_species.json")
    matches: dict[str, SpeciesMatch] = {}
    for text in texts:
        if not text:
            continue
        norm = normalize(text)
        for sp in data["species"]:
            for alias in sp["aliases"]:
                if contains_phrase(norm, alias):
                    matches.setdefault(sp["key"], SpeciesMatch(sp["key"], sp["common_name"], alias))
                    break
    return list(matches.values())


def species_key_for(*texts: str) -> str | None:
    """Map free text to a known species key in species.json (longest alias wins)."""
    best: tuple[int, str] | None = None
    for text in texts:
        if not text:
            continue
        norm = normalize(text)
        for sp in load_seed("species.json")["species"]:
            for alias in sp["aliases"]:
                if contains_phrase(norm, alias) and (best is None or len(alias) > best[0]):
                    best = (len(alias), sp["key"])
    return best[1] if best else None
