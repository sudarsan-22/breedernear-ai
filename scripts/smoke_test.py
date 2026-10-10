"""Pre-submission smoke test against a deployed URL (docs/implementation/06-testing-and-evaluation.md §4).

Usage:
    python scripts/smoke_test.py https://<service>.run.app [--no-ai]

Uses only the standard library. Exits non-zero if any check fails. --no-ai skips the one Gemini call.
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

GUEST = str(uuid.uuid4())
results: list[tuple[bool, str]] = []


def call(base: str, method: str, path: str, body: dict | None = None, timeout: int = 60) -> tuple[int, dict]:
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "X-Guest-Id": GUEST})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(("PASS " if ok else "FAIL ") + label)


def main(base: str, ai: bool) -> int:
    base = base.rstrip("/")
    start = time.time()
    status, health = call(base, "GET", "/api/health")
    check(status == 200 and health.get("status") == "ok", f"health {health}")
    check(not str(health.get("model", "")).startswith("gemini-2"), "model is not a retiring gemini-2.x")

    req = urllib.request.Request(base + "/")
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode()
    check("BreederNear AI" in page and "Not veterinary advice" in page, "web app served with disclaimer")

    status, pets = call(base, "GET", "/api/pets?district=tiruppur")
    levels = {p["trust_level"] for p in pets.get("results", [])}
    check(status == 200 and pets.get("total", 0) >= 30, f"pets near Tiruppur: {pets.get('total')}")
    check("BLOCKED" not in levels, "no BLOCKED listing is shown to buyers")
    check(any(p.get("photo") for p in pets.get("results", [])), "sample listings have photos")

    status, breeders = call(base, "GET", "/api/breeders?district=tiruppur")
    count = len(breeders.get("breeders", []))
    check(status == 200 and count >= 10, f"breeders near Tiruppur: {count}")

    status, kit = call(base, "GET", "/api/starter-kit?species=budgie&count=2")
    check(status == 200 and kit.get("min_cage_cm") == [60, 40, 45], "starter kit uses the welfare cage size")

    status, quiz = call(base, "POST", "/api/recommend", {"animal_group": "bird", "home_type": "flat",
                                                         "has_young_children": True, "budget_inr": 3000})
    check(status == 200 and quiz["options"][0]["species_key"] == "budgerigar", "quiz suggests budgies first")

    if ai:
        path = f"/apps/breedernear/users/{GUEST}/sessions"
        status, session = call(base, "POST", path, {"state": {"mode": ""}})
        check(status == 200, "agent session created")
        status, events = call(base, "POST", "/run", {
            "app_name": "breedernear", "user_id": GUEST, "session_id": session.get("id"),
            "new_message": {"role": "user", "parts": [{"text": "Hello! In one sentence, what can you do?"}]}},
            timeout=120)
        text = "".join(p.get("text", "") for e in (events if isinstance(events, list) else [])
                       for p in (e.get("content") or {}).get("parts", []) if not p.get("thought"))
        check(status == 200 and len(text) > 10, f"agent replied: {text[:80]!r}")

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed in {time.time() - start:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], "--no-ai" not in sys.argv))
