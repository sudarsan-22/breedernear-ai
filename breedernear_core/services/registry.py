"""Lookup in the SIMULATED State Animal Welfare Board dog-breeder registry."""

from datetime import date

from breedernear_core.data import load_seed


def sawb_status(registration_no: str | None, today: date | None = None) -> str:
    """Return "valid", "expired", "unknown" (not in registry) or "missing" (not provided)."""
    if not registration_no or not registration_no.strip():
        return "missing"
    today = today or date.today()
    wanted = registration_no.strip().upper()
    for reg in load_seed("sawb_registry_sample.json")["registrations"]:
        if reg["registration_no"].upper() == wanted:
            return "valid" if date.fromisoformat(reg["valid_until"]) >= today else "expired"
    return "unknown"
