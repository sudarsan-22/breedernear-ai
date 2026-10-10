"""The submission form's brief description fits its 1024-character field and names the required services."""

import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "submission" / "04-brief-description.md"


def _text() -> str:
    return re.search(r"```text\n(.*?)\n```", DOC.read_text(), re.DOTALL).group(1)


def test_fits_the_form_field():
    assert len(_text()) <= 1024


def test_names_every_service_the_rules_ask_about():
    text = _text()
    for name in ("Firebase", "Firestore", "Cloud Run", "Gemini"):
        assert name in text
