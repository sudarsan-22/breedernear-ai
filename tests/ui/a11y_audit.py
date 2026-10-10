"""Accessibility audit of every screen with axe-core in headless Chromium (light and dark mode).

Run against a local server: python tests/ui/a11y_audit.py http://localhost:8765
Used by tests/ui/test_accessibility.py; prints one line per problem.
"""

import os
import sys

AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
PASSWORD = "demo12345"
CUSTOMER_TABS = ["pets", "breeders", "ai", "account"]
SELLER_TABS = ["dashboard", "listings", "enquiries", "sell", "farm", "ai"]


def _axe(page, label: str) -> list[str]:
    if not page.evaluate("typeof window.axe !== 'undefined'"):
        page.add_script_tag(url=os.environ.get("AXE_URL", AXE_URL))
    result = page.evaluate("(tags) => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
    problems = []
    for v in result["violations"]:
        for node in v["nodes"][:4]:
            problems.append(f"[{label}] {v['id']} ({v['impact']}): {' '.join(node['target'])} | "
                            f"{node.get('failureSummary', '').splitlines()[-1].strip()[:140]}")
    return problems


def _overflow(page, label: str) -> list[str]:
    wide = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    return [f"[{label}] page scrolls sideways by {wide}px"] if wide > 1 else []


def _login(page, base: str, email: str) -> None:
    page.goto(base)
    page.evaluate("localStorage.clear(); sessionStorage.clear()")
    page.goto(base)
    page.wait_for_selector("#auth-login")
    page.fill("#auth-login", email)
    page.fill("#auth-password", PASSWORD)
    page.get_by_role("button", name="Log in", exact=True).last.click()
    page.wait_for_function("['#pets', '#dashboard'].includes(location.hash)")
    page.wait_for_load_state("networkidle")


def _screen(page, base: str, route: str, label: str) -> list[str]:
    page.goto(f"{base}/#{route}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    return _axe(page, label) + _overflow(page, label)


def audit(base: str, chromium: str | None = None, width: int = 390) -> list[str]:
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium) if chromium else pw.chromium.launch()
        for scheme in ("light", "dark"):
            page = browser.new_page(viewport={"width": width, "height": 800}, color_scheme=scheme,
                                    reduced_motion="reduce")      # no fade-ins mid-measurement
            errors: list[str] = []
            page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
            page.goto(base)
            page.evaluate("localStorage.clear(); sessionStorage.clear()")
            page.goto(base)
            page.wait_for_selector("#auth-login")
            problems += _axe(page, f"{scheme} login") + _overflow(page, f"{scheme} login")
            page.get_by_role("button", name="Sign up", exact=True).first.click()
            page.wait_for_timeout(300)
            problems += _axe(page, f"{scheme} signup")

            _login(page, base, "priya.customer@example.com")
            for tab in CUSTOMER_TABS:
                problems += _screen(page, base, tab, f"{scheme} customer {tab}")
            page.goto(f"{base}/#pets")
            page.wait_for_selector(".pet")
            page.locator(".pet").first.click()
            page.wait_for_selector("#sheet[open] #sheet-content .fact, #sheet[open] #sheet-content .callout")
            page.wait_for_timeout(400)
            problems += _axe(page, f"{scheme} listing sheet")
            if not page.evaluate("document.getElementById('sheet').contains(document.activeElement)"):
                problems.append(f"[{scheme} listing sheet] focus is not inside the open sheet")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            if page.evaluate("document.getElementById('sheet').open"):
                problems.append(f"[{scheme} listing sheet] Escape does not close the sheet")
            page.click("#cart-btn")
            page.wait_for_selector("#sheet[open]")
            page.wait_for_timeout(400)
            problems += _axe(page, f"{scheme} cart sheet")
            page.keyboard.press("Escape")

            _login(page, base, "karthik.seller@example.com")
            for tab in SELLER_TABS:
                problems += _screen(page, base, tab, f"{scheme} seller {tab}")
            problems += [f"[{scheme}] script error: {e}" for e in errors]
            page.close()
        browser.close()
    return problems


if __name__ == "__main__":
    found = audit(sys.argv[1].rstrip("/"), os.environ.get("CHROMIUM"), int(os.environ.get("WIDTH", "390")))
    print("\n".join(found) or "no problems")
    print(f"{len(found)} problems")
