"""Code checks on what the agents say, on top of the prompts (docs/product/03-responsible-ai-and-safety.md).

Prompts make good replies likely; these checks make two bad replies impossible to deliver:
- medicine names or doses (a wrong drug or amount can kill a small bird), and
- a protected native species presented as something to buy, sell or keep.
"""

import re

from breedernear_core.safety.species_rules import find_protected

# Named veterinary drugs and dose amounts. Plain words like "dose" are allowed, so a reply can still say
# "I can't suggest medicines or doses".
_DRUG = re.compile(
    r"\b\d+(\.\d+)?\s?(mg|mcg|µg|iu)\b|\bmg\s?/\s?kg\b|\b\d+\s?drops?\b"
    r"|\b(ivermectin|enrofloxacin|baytril|metronidazole|doxycycline|amoxicillin|amoxycillin|tetracycline"
    r"|oxytetracycline|ciprofloxacin|tylosin|sulfa\w*|trimethoprim|ronidazole|toltrazuril|fenbendazole"
    r"|albendazole|praziquantel|levamisole|piperazine|meloxicam|paracetamol|ibuprofen|dexamethasone"
    r"|prednisolone|nystatin|fluconazole|itraconazole)\b",
    re.IGNORECASE,
)
# A reply that names a protected species must also say it can't be traded.
_LEGAL_WARNING = re.compile(
    r"protected|illegal|not allowed|not legal|wild ?life|can(no|')t be (sold|bought|kept|traded|listed)"
    r"|banned|prohibited|against the law",
    re.IGNORECASE,
)

MEDICINE_REPLY = (
    "I can't recommend medicines or doses: the wrong drug or amount can seriously harm a pet, especially "
    "a small bird. Please see a veterinarian today (an avian vet for birds). Go sooner if your pet stops "
    "eating or drinking, breathes with effort, sits fluffed up or very quiet, has diarrhoea, or has "
    "discharge from the eyes or nose. Keep it warm, quiet and away from other pets until then."
)
PROTECTED_REPLY = (
    "Native Indian species such as rose-ringed and Alexandrine parakeets, munias, red avadavats, mynas and "
    "star tortoises are protected. Buying, selling or keeping them is illegal under the Wild Life "
    "(Protection) Act, 1972, so BreederNear never lists them. Legal pets that make great companions: "
    "budgies, cockatiels, lovebirds, zebra or society finches, and canaries."
)


def unsafe_reply(text: str) -> str | None:
    """The safe replacement for a reply that must not be shown, or None if the reply is fine."""
    if not text:
        return None
    if _DRUG.search(text):
        return MEDICINE_REPLY
    if find_protected(text) and not _LEGAL_WARNING.search(text):
        return PROTECTED_REPLY
    return None


def redact_args(args: dict) -> dict:
    """Tool arguments for the logs: IDs and short values kept, free text reduced to its length."""
    out = {}
    for key, value in args.items():
        if isinstance(value, str) and len(value) > 40:
            out[key] = f"<text, {len(value)} chars>"
        elif isinstance(value, list) and len(value) > 5:
            out[key] = f"<{len(value)} items>"
        else:
            out[key] = value
    return out
