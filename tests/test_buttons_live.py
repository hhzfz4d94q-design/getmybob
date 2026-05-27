"""Functional button smoke test for the live getmemyjob dashboard.

Loads https://getmemyjob.officebeatllc.com/amit-arora.html in a headless
Chromium browser and verifies, end-to-end:

  - Page loads with zero JavaScript console errors (catches the
    "unescaped apostrophe broke ALL buttons" class of bug)
  - Header has exactly the 3 expected visible buttons + correct labels
  - Each dropdown (Account ⌄ / More ⋯) opens on click and shows the
    expected menu items
  - First job card has all expected action buttons with sensible
    behavior:
      Apply now → has an http(s) href
      Prep materials → click opens prep-modal (which becomes visible)
      Warm intro → href is a LinkedIn URL with NO network=["F","S"]
                    filter (the bug fixed in commit 61142cc)
      Mark Applied → button exists

Run via:  python3 tests/test_buttons_live.py
Exits 0 on all-green, 1 on any failure. Saves a screenshot on failure
to tests/failure-screenshot.png so CI artifacts capture it.

Requires:
  pip install playwright
  python -m playwright install chromium --with-deps
"""
import os, sys, re
from playwright.sync_api import sync_playwright, Page, Error as PWError

URL = os.environ.get("DASHBOARD_URL", "https://getmemyjob.officebeatllc.com/amit-arora.html")
SCREENSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failure-screenshot.png")

PASS = 0
FAIL = 0
console_errors: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  ({detail})")


def run() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}")
                if msg.type in ("error",) else None)

        print(f"Loading {URL}")
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        except PWError as e:
            check(f"page loads", False, f"goto failed: {e}")
            try: page.screenshot(path=SCREENSHOT, full_page=True)
            except Exception: pass
            browser.close()
            return 1

        # Wait for the script block to have executed (the header is rendered in static HTML
        # but the inline JS must run for handlers to bind — give it 2s)
        page.wait_for_timeout(2000)

        # -------------------- 1. No console errors during load --------------------
        print("\n[1] Page load — no JavaScript errors:")
        # Filter out benign noise (resource 404s on static assets we don't care about)
        real_errors = [e for e in console_errors
                       if not any(skip in e for skip in (
                           "favicon", "og-card", "manifest",
                           # These come from extension content-scripts on pages we don't own
                       ))]
        check("no JS console errors / page errors during load",
              len(real_errors) == 0,
              f"{len(real_errors)} error(s): {real_errors[:3]}")

        # -------------------- 2. Three visible header buttons --------------------
        print("\n[2] Header — 3 visible buttons present with correct labels:")
        # Visible header buttons: Find new jobs, Account, More
        find_btn = page.locator("#refresh-btn")
        check("'⟳ Find new jobs' button exists and is visible",
              find_btn.count() == 1 and find_btn.first.is_visible(),
              f"count={find_btn.count()}")
        if find_btn.count() == 1:
            text = (find_btn.first.text_content() or "").strip()
            check("'Find new jobs' label text is correct",
                  "Find new jobs" in text, f"got: {text!r}")

        account_btn = page.locator("#account-btn")
        check("'Account ⌄' button exists and is visible",
              account_btn.count() == 1 and account_btn.first.is_visible(),
              f"count={account_btn.count()}")
        if account_btn.count() == 1:
            text = (account_btn.first.text_content() or "").strip()
            check("'Account' label text is correct",
                  "Account" in text, f"got: {text!r}")

        more_btn = page.locator(".header-actions button:has-text('More')")
        check("'More ⋯' button exists and is visible",
              more_btn.count() >= 1 and more_btn.first.is_visible(),
              f"count={more_btn.count()}")

        # -------------------- 3. Account dropdown opens with correct items --------------------
        print("\n[3] Account dropdown — opens with Change password + Sign out:")
        # Close any open dropdown first
        page.locator("body").click(position={"x": 5, "y": 5})
        page.wait_for_timeout(200)
        if account_btn.count() == 1:
            account_btn.first.click()
            page.wait_for_timeout(300)
            # The dropdown is the first .header-more-wrap (which contains #account-btn)
            account_wrap = page.locator(".header-more-wrap").filter(has=page.locator("#account-btn"))
            check("Account dropdown opens (.open class applied)",
                  "open" in (account_wrap.first.get_attribute("class") or ""),
                  f"class: {account_wrap.first.get_attribute('class')!r}")
            menu = account_wrap.locator(".header-more-menu")
            check("Account dropdown menu is visible",
                  menu.first.is_visible(),
                  f"display style was hidden")
            menu_text = (menu.first.text_content() or "")
            check("Account menu contains 'Change password'",
                  "Change password" in menu_text, f"menu text: {menu_text!r}")
            check("Account menu contains 'Sign out'",
                  "Sign out" in menu_text, f"menu text: {menu_text!r}")
            # Change password link goes to /account.html
            cp_link = account_wrap.locator("a", has_text="Change password")
            if cp_link.count() == 1:
                href = cp_link.first.get_attribute("href") or ""
                check("Change password link points to /account.html",
                      href.endswith("/account.html"), f"href: {href!r}")

        # -------------------- 4. More dropdown opens with correct items --------------------
        print("\n[4] More dropdown — opens with 4 app actions:")
        page.locator("body").click(position={"x": 5, "y": 5})
        page.wait_for_timeout(200)
        if more_btn.count() >= 1:
            more_btn.first.click()
            page.wait_for_timeout(300)
            # The More wrap is the .header-more-wrap that does NOT contain #account-btn
            more_wrap = page.locator(".header-more-wrap").filter(has=more_btn.first)
            check("More dropdown opens (.open class applied)",
                  "open" in (more_wrap.first.get_attribute("class") or ""),
                  f"class: {more_wrap.first.get_attribute('class')!r}")
            menu = more_wrap.locator(".header-more-menu")
            menu_text = (menu.first.text_content() or "")
            for label in ["Re-match my profile", "Resume", "LinkedIn Contacts", "Preferences"]:
                check(f"More menu contains '{label}'",
                      label in menu_text,
                      f"missing from: {menu_text!r}")

        # -------------------- 5. First job card buttons --------------------
        print("\n[5] First job card — action buttons present and well-formed:")
        page.locator("body").click(position={"x": 5, "y": 5})
        page.wait_for_timeout(200)
        first_card = page.locator(".card").first
        if first_card.count() == 0:
            check("at least one job card on page", False, "no .card elements")
        else:
            check("at least one job card on page", True)
            # Apply now anchor
            apply_a = first_card.locator("a.btn.primary", has_text="Apply")
            check("'Apply now' button exists on first card",
                  apply_a.count() >= 1,
                  f"count={apply_a.count()}")
            if apply_a.count() >= 1:
                href = apply_a.first.get_attribute("href") or ""
                check("Apply now href is an http(s) URL",
                      href.startswith("https://") or href.startswith("http://"),
                      f"href: {href!r}")

            # Prep materials button - click and check modal opens
            prep_btn = first_card.locator("button", has_text="Prep materials")
            check("'Prep materials' button exists on first card",
                  prep_btn.count() >= 1,
                  f"count={prep_btn.count()}")

            # Warm intro — verify NO network filter (the bug we fixed)
            warm = first_card.locator("a.warm-intro")
            if warm.count() >= 1:
                href = warm.first.get_attribute("href") or ""
                check("Warm intro href is a LinkedIn URL",
                      "linkedin.com" in href, f"href: {href!r}")
                check("Warm intro href does NOT contain the network=[F,S] filter (regression test)",
                      "network=" not in href and "%5B%22F%22" not in href,
                      f"href: {href!r}")
            else:
                print("  - (no warm-intro on first card — non-fatal, depends on company)")

            # Mark Applied button
            mark = first_card.locator("button.btn.track")
            check("'Mark Applied' button exists on first card",
                  mark.count() >= 1,
                  f"count={mark.count()}")

        # -------------------- 6. Prep materials click opens modal --------------------
        print("\n[6] Prep materials click — modal becomes visible:")
        if first_card.count() >= 1:
            prep_btn = first_card.locator("button", has_text="Prep materials")
            if prep_btn.count() >= 1:
                # Before click, modal should not have .show
                modal = page.locator("#prep-modal")
                before_class = modal.get_attribute("class") or ""
                check("prep-modal exists in DOM (before click)",
                      modal.count() == 1, "")
                # Click and wait briefly
                prep_btn.first.click()
                page.wait_for_timeout(500)
                after_class = modal.get_attribute("class") or ""
                check("prep-modal gains .show class after Prep materials click",
                      "show" in after_class,
                      f"class went {before_class!r} -> {after_class!r}")

        # -------------------- 7. Save screenshot on any failure --------------------
        if FAIL > 0:
            try:
                page.screenshot(path=SCREENSHOT, full_page=True)
                print(f"\n  💾 Screenshot saved: {SCREENSHOT}")
            except Exception as e:
                print(f"\n  (could not save screenshot: {e})")

        browser.close()

    print(f"\n{'='*48}")
    print(f"Result: {PASS} passed, {FAIL} failed")
    if console_errors:
        print(f"\nAll console messages captured ({len(console_errors)}):")
        for line in console_errors[:20]:
            print(f"  {line}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
