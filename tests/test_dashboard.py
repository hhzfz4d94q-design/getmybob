"""Verify rendered dashboards (geetu.html, amit-arora.html) are well-formed.

Run via:  python3 tests/test_dashboard.py
Pulls HTML from origin/main via the GitHub API.
"""
import os, sys, json, re, urllib.request, subprocess, tempfile

PAT = os.environ.get("PAT") or ""
OWNER = "hhzfz4d94q-design"
REPO = "getmybob"
SLUGS = ["geetu", "amit-arora"]

PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✓ {label}")
    else:    FAIL += 1; print(f"  ✗ {label}  {detail}")

def fetch(path):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}?ref=main"
    headers = {"Accept": "application/vnd.github.raw"}
    if PAT: headers["Authorization"] = f"Bearer {PAT}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        return r.read().decode("utf-8")

for slug in SLUGS:
    print(f"\n=== {slug}.html ===")
    try:
        html = fetch(f"{slug}.html")
    except Exception as e:
        print(f"  ✗ Could not fetch {slug}.html: {e}")
        FAIL += 1
        continue

    check(f"non-empty HTML ({len(html):,} bytes)", len(html) > 50_000)

    # Card count
    cards = re.findall(r'<div class="card"[^>]*data-fp="[^"]+"', html)
    check(f"renders >= 5 job cards ({len(cards)})", len(cards) >= 5)

    # Apply button is <a href>, not <button>
    apply_anchors = re.findall(r'<a class="btn primary" href="[^"]+"[^>]*>Apply now', html)
    apply_buttons = re.findall(r'<button class="btn primary"[^>]*>Apply now', html)
    check("Apply button is <a href> (copy/paste-safe in email)", len(apply_anchors) > 0)
    check("No old <button> Apply variant remains", len(apply_buttons) == 0)

    # Careers-fallback link below Apply (the email-safe fallback)
    fallbacks = re.findall(r'class="careers-fallback"', html)
    check(f"careers-fallback link present on >= 5 cards ({len(fallbacks)})", len(fallbacks) >= 5)

    # Daily Focus panel exists
    check("Daily Focus panel block present", '<div id="focus-panel"' in html)
    check("Focus list container present", '<div id="focus-list"' in html)
    check("refreshFocusPanel JS present", "function refreshFocusPanel" in html)

    # Wizard step: install Helper extension
    check("Install-extension wizard step present", "Install the Helper Chrome extension" in html)
    check("verify-extension action handler present", '"verify-extension"' in html)

    # Wizard step: application profile
    check("App-profile wizard step present", "Application profile (so we can auto-fill" in html)
    check("save-app-profile action present", '"save-app-profile"' in html)
    check("Phone input present in app-profile step", 'id="wiz-app-phone"' in html)
    check("LinkedIn input present", 'id="wiz-app-linkedin"' in html)
    check("Work-authorization select present", 'id="wiz-app-workauth"' in html)

    # Single-quote bug regression check
    check("No raw wizWtOnNum('titles') (would break JS parse)",
          "wizWtOnNum('titles')" not in html or "wizWtOnNum(&apos;titles&apos;)" in html)

    # All script blocks parse cleanly via Node
    biggest = max(re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL), key=len)
    with tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w") as f:
        f.write(biggest)
        jsfile = f.name
    try:
        out = subprocess.run(
            ["node", "-e", f"new Function(require('fs').readFileSync('{jsfile}','utf-8'))"],
            capture_output=True, text=True, timeout=20,
        )
        check("Largest <script> block parses as valid JS", out.returncode == 0,
              out.stderr.strip().split(chr(10))[-1][:200] if out.returncode else "")
    except subprocess.TimeoutExpired:
        check("JS parse check ran", False, "timeout")
    os.unlink(jsfile)

    # GHOST_DAYS reflected in dashboard
    ghost_old = re.findall(r"data-listed-days=\"\d+\"", html)
    check(f"data-listed-days populated on cards ({len(ghost_old)} cards)", len(ghost_old) >= 5)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
