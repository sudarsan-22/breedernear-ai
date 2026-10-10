"""Live agent evals: real Gemini, sample data in memory. Run: pytest -m live tests/evals

Each run is appended to evals/runs.jsonl; evals/RESULTS.md summarises every recorded run for the current
model, so running the suite several times gives a repeatability figure (scripts/run_evals.sh N).
"""

import datetime
import json
from pathlib import Path

import pytest

RESULTS: list[tuple[str, str, str]] = []  # (case id, outcome, title)
EVALS = Path(__file__).resolve().parents[2] / "evals"


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
        result = report.outcome
        if report.failed and call.excinfo is not None and not call.excinfo.errisinstance(AssertionError):
            result = f"error: {call.excinfo.typename}"     # e.g. the connection to Gemini dropped
        RESULTS.append((item.name.removeprefix("test_").split("_")[0].upper(), result, doc))


def _summary(runs: list[dict], model: str) -> str:
    titles: dict[str, str] = {}
    passes: dict[str, int] = {}
    counts: dict[str, int] = {}
    errors: dict[str, int] = {}
    for run in runs:
        for case in run["cases"]:
            titles[case["id"]] = case["title"]
            counts[case["id"]] = counts.get(case["id"], 0) + 1
            passes[case["id"]] = passes.get(case["id"], 0) + (case["outcome"] == "passed")
            errors[case["id"]] = errors.get(case["id"], 0) + case["outcome"].startswith("error")
    total_pass, total = sum(passes.values()), sum(counts.values())
    wrong = total - total_pass - sum(errors.values())
    full = sum(1 for r in runs if all(c["outcome"] == "passed" for c in r["cases"]))
    run_rows = "\n".join(
        f"| {i} | {r['date']} | {sum(c['outcome'] == 'passed' for c in r['cases'])}/{len(r['cases'])} |"
        for i, r in enumerate(runs, 1))
    case_rows = "\n".join(
        f"| {cid} | {'✅' if passes[cid] == counts[cid] else '⚠️'} {passes[cid]}/{counts[cid]}"
        f"{f' ({errors[cid]} network error)' if errors[cid] else ''} | {titles[cid]} |"
        for cid in sorted(titles))
    return (
        "# Agent eval results\n\n"
        f"Model `{model}`, real Gemini, sample data in memory. **{len(runs)} full runs: "
        f"{total_pass}/{total} case runs passed ({100 * total_pass / total:.0f}%); "
        f"{full} of {len(runs)} runs passed every case. Wrong answers: {wrong}; "
        f"network errors: {sum(errors.values())}.**\n\n"
        "A network error means the connection to Gemini dropped before a reply arrived; it counts as a miss "
        "but is not a wrong answer.\n\n"
        "Gemini is not deterministic, so each case is run several times and the pass count is reported, "
        "not a single best run. Reproduce with `scripts/run_evals.sh 3` (needs Google Cloud credentials); "
        "cases and what they check: `tests/evals/test_agent_evals.py`.\n\n"
        f"| Run | Date | Passed |\n|---|---|---|\n{run_rows}\n\n"
        f"| Case | Passed | What it checks |\n|---|---|---|\n{case_rows}\n"
    )


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    from breedernear_core.config import get_settings

    model = get_settings().breedernear_model
    EVALS.mkdir(exist_ok=True)
    log = EVALS / "runs.jsonl"
    with log.open("a") as f:
        f.write(json.dumps({"date": datetime.date.today().isoformat(), "model": model, "cases": [
            {"id": cid, "outcome": o, "title": t} for cid, o, t in RESULTS]}) + "\n")
    runs = [r for r in map(json.loads, log.read_text().splitlines()) if r["model"] == model]
    (EVALS / "RESULTS.md").write_text(_summary(runs, model))
