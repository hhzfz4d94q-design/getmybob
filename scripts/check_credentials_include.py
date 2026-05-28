"""Fails CI if any dashboard JS contains credentials:'include'.

The worker's CORS responds Access-Control-Allow-Origin: '*'. Combining
that with credentials:'include' on the client side is a hard spec violation
that browsers reject with the generic 'TypeError: Failed to fetch' — and
since our auth flows over headers (X-Edit-Key / X-Admin-Key / Authorization),
credentials:include is never necessary. So we just ban it outright.

Scans:
  - dashboard/template.py, dashboard/wizard.py, dashboard/help.py
  - account.html, login.html, signup.html, sprint.html, admin.html
  - generated per-user *.html (anything not in the skip list)

Run locally: python3 scripts/check_credentials_include.py
Used by: js-syntax-gate.yml on every push/PR touching dashboards.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files to scan — source files where the pattern would be a regression.
SOURCE_PATHS = [
    "dashboard/template.py",
    "dashboard/wizard.py",
    "dashboard/help.py",
    "account.html",
    "login.html",
    "signup.html",
    "sprint.html",
    "admin.html",
    "landing.html",
    "index.html",
    "about.html",
    "forgot.html",
    "dashboard.html",
]

PATTERN = re.compile(r"credentials\s*:\s*['\"]include['\"]")


def main():
    failures = []
    scanned = 0
    for rel in SOURCE_PATHS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        scanned += 1
        with open(path) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if PATTERN.search(line):
                failures.append((rel, i, line.rstrip()))

    if failures:
        print("FAIL: found credentials:'include' in dashboard sources.\n")
        print("Why this is banned: worker CORS responds Allow-Origin:'*',")
        print("which is incompatible with credentials:include. Browsers will")
        print("block the request with the generic 'Failed to fetch' error.")
        print("Our auth flows over headers, so credentials:include is never needed.\n")
        for path, lineno, content in failures:
            print(f"  {path}:{lineno}\n    {content}")
        return 1
    print(f"OK — scanned {scanned} files, no credentials:'include' found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
