"""Scam-language signals in listing text (English and romanised Tamil)."""

import re

# (label shown to users, pattern). Patterns run on lowercased text.
_SIGNALS: list[tuple[str, str]] = [
    ("asks for full payment in advance",
     r"\b(full|100\s*%?|complete)\s*(advance|payment\s*first)|\badvance\s*(payment\s*)?(only|mattum)\b"
     r"|\bpay(ment)?\s*first\b|\bgpay\s*first\b"),
    ("refuses visits before payment",
     r"\bno\s*(direct\s*)?visit|\bvisit\s*(not\s*allowed|illa)\b|\bno\s*meet(ing)?\b"),
    ("courier or parcel only, no handover in person",
     r"\b(courier|parcel)\s*(only|mattum)\b|\bonly\s*(by\s*)?(courier|parcel)\b|\btrain\s*parcel\b"),
    ("pressure to decide quickly",
     r"\btoday\s*only\b|\burgent\s*sale\b|\bprice\s*will\s*increase\b|\blast\s*(one|pair)\s*left\b"),
    ("delivery anywhere in India without seeing the animal",
     r"\b(all|across)\s*india\s*delivery\b|\bdelivery\s*all\s*(over\s*)?india\b"),
]


def find_scam_signals(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [label for label, pattern in _SIGNALS if re.search(pattern, lowered)]
