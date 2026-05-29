"""Frozen-fixture tests for scrapers.

Why: each scraper parses a public ATS API response into our internal job
dict. If the API silently changes shape (new wrapping, missing field), the
scraper either crashes or returns junk that the matcher silently scores
low. These tests freeze a known response and assert the parsed output.

We mock urlopen at the scraper boundary so no network access is needed.
"""
import json
import os
import sys
import unittest.mock as mock
from io import BytesIO

# Make repo root importable so `import scrapers.greenhouse` works in pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scrapers.greenhouse as gh


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _mock_urlopen(fixture_name):
    """Return a context-manager mock that yields the named fixture JSON."""
    with open(os.path.join(FIXTURES, fixture_name)) as f:
        body = f.read().encode()
    cm = mock.MagicMock()
    cm.__enter__.return_value = cm
    cm.read.return_value = body
    return mock.patch("scrapers._http.urlopen", return_value=cm)


passed = 0
failed = 0
def check(cond, label):
    global passed, failed
    if cond:
        print(f"  ✓ {label}")
        passed += 1
    else:
        print(f"  ✗ {label}")
        failed += 1


print("=== greenhouse scraper fixture tests ===\n")
with _mock_urlopen("greenhouse_devoted.json"):
    jobs = gh.fetch_greenhouse("devotedhealth")

check(len(jobs) == 2, f"parses 2 jobs (got {len(jobs)}); skips null entry defensively")
if jobs:
    j0 = jobs[0]
    check(j0.get("source") == "greenhouse", "source tag set to 'greenhouse'")
    check(j0.get("company_slug") == "devotedhealth", "company_slug echoed from arg")
    check("VP" in (j0.get("title") or ""), f"title parsed: {j0.get('title','')[:50]}")
    check("Remote" in (j0.get("location") or ""), "location parsed")
    check(j0.get("url","").startswith("https://"), "url present")
    sal = gh._extract_greenhouse_salary({
        "metadata": [{"name": "Salary Range", "value": "$200K - $260K"}]
    })
    check("200K" in sal or "200" in sal, "salary extractor pulls from metadata")
    sal2 = gh._extract_greenhouse_salary({
        "pay_input_ranges": [{"min_cents": 20000000, "max_cents": 26000000, "currency_type": "USD"}]
    })
    check("200,000" in sal2, "salary extractor pulls from pay_input_ranges cents")

print(f"\n========================================")
print(f"Result: {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
