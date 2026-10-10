"""Accessibility: axe-core (WCAG 2.2 A/AA rules) on every screen of both apps, light and dark, at phone,
narrow-phone and desktop widths; no sideways scrolling; sheets take focus and close with Escape.

Needs Playwright with Chromium and internet access (axe-core loads from cdnjs). Skipped when Playwright is
not installed, as in CI. Run: pytest -m ui tests/ui   (CHROMIUM=/path/to/chrome to use a local build)
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.ui

from tests.ui.a11y_audit import audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "BREEDERNEAR_BACKEND": "memory"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{base}/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.5)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.mark.parametrize("width", [320, 390, 1280])
def test_no_accessibility_problems(server, width):
    problems = audit(server, os.environ.get("CHROMIUM"), width)
    assert problems == [], "\n".join(problems)
