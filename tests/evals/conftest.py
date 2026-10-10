"""Live agent evals: real Gemini, sample data in memory. Run: pytest -m live tests/evals"""

import datetime
from pathlib import Path

import pytest

RESULTS: list[tuple[str, str, str]] = []  # (case id, outcome, title)


@pytest.fixture(scope="session")
def harness():
    from tests.evals.harness import Harness

    h = Harness()
    yield h
    h.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and item.get_closest_marker("live") and "test_agent_evals" in item.nodeid:
        doc = (item.function.__doc__ or "").strip().splitlines()[0]
        RESULTS.append((item.name.removeprefix("test_"), report.outcome, doc))


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    from breedernear_core.config import get_settings

    passed = sum(1 for _, o, _ in RESULTS if o == "passed")
    rows = "\n".join(
        f"| {cid.split('_')[0].upper()} | {'✅ pass' if o == 'passed' else '❌ ' + o} | {title} |"
        for cid, o, title in RESULTS
    )
    out = Path(__file__).resolve().parents[2] / "evals" / "RESULTS.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        f"# Agent eval results\n\nRun on {datetime.date.today().isoformat()} "
        f"with `{get_settings().breedernear_model}` "
        f"(real Gemini, sample data in memory): **{passed}/{len(RESULTS)} passed**.\n\n"
        "Reproduce with `pytest -m live tests/evals` (needs Google Cloud credentials). Cases and what they "
        "check: `tests/evals/test_agent_evals.py`.\n\n| Case | Result | What it checks |\n|---|---|---|\n"
        + rows
        + "\n"
    )
