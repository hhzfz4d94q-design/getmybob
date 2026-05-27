"""Parser tests for the highest-volume ATS scrapers.

Each test monkey-patches fetch_jobs.fetch_json to return a fixture instead
of hitting the live API. This catches:
  - vendor response-shape drift (key renames, nested moves)
  - silent dropping of valid jobs after refactors
  - crashes on empty boards / malformed entries

Run via:  python3 tests/test_scrapers.py
Exits non-zero on any failure (matches the existing tests/ style).
"""
import os
import sys
import json
import pathlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fetch_jobs

FIX = pathlib.Path(__file__).parent / "fixtures" / "ats"

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  ({detail})")


def with_fixture(fixture_name, fn, *args, **kwargs):
    """Run fn with fetch_jobs.fetch_json patched to return the JSON fixture."""
    real = fetch_jobs.fetch_json
    data = json.loads((FIX / fixture_name).read_text())
    fetch_jobs.fetch_json = lambda url: data
    try:
        return fn(*args, **kwargs)
    finally:
        fetch_jobs.fetch_json = real


# ----------------------------------------------------------------------
# Greenhouse
# ----------------------------------------------------------------------
print("Greenhouse:")
jobs = with_fixture("greenhouse_stripe.json", fetch_jobs.fetch_greenhouse, "stripe")
check("happy fixture returns >= 2 jobs", len(jobs) >= 2, f"got {len(jobs)}")
if jobs:
    j = jobs[0]
    check("each job has expected keys",
          {"source", "company_slug", "company_name", "external_id", "title", "location", "url", "posted_at", "description"} <= j.keys(),
          f"missing: {{'source','company_slug','company_name','external_id','title','location','url','posted_at','description'}} - {set(j.keys())}")
    check("source is tagged 'greenhouse'", j["source"] == "greenhouse", f"got {j['source']}")
    check("location is a flat string (not the nested {'name': ...})", isinstance(j["location"], str), f"got {type(j['location']).__name__}")
    check("url starts with https://", j["url"].startswith("https://"), f"got {j['url']!r}")
    check("HTML in content is stripped from description", "<p>" not in j["description"] and "<" not in j["description"], f"got {j['description']!r}")
    check("posted_at is non-empty", bool(j["posted_at"]), f"got {j['posted_at']!r}")

empty = with_fixture("greenhouse_empty.json", fetch_jobs.fetch_greenhouse, "empty-co")
check("empty board returns empty list, doesn't raise", empty == [], f"got {empty}")

malformed = with_fixture("greenhouse_malformed.json", fetch_jobs.fetch_greenhouse, "weird-co")
check("malformed entries are tolerated (doesn't raise)", isinstance(malformed, list), "should return a list, not raise")
# We don't require it to filter — just not crash. Some scrapers emit "" for missing fields.
check("at least the well-formed job survives", any(j["external_id"] == "1" for j in malformed), f"got {[j.get('external_id') for j in malformed]}")


# ----------------------------------------------------------------------
# Lever
# ----------------------------------------------------------------------
print("\nLever:")
jobs = with_fixture("lever_canva.json", fetch_jobs.fetch_lever, "canva")
check("happy fixture returns >= 2 jobs", len(jobs) >= 2, f"got {len(jobs)}")
if jobs:
    j = jobs[0]
    check("each job has expected keys",
          {"source", "company_slug", "title", "location", "url"} <= j.keys(),
          f"got keys {set(j.keys())}")
    check("source is tagged 'lever'", j["source"] == "lever", f"got {j['source']}")
    check("title comes from 'text' field", j["title"] == "Staff Engineer, Editor Platform", f"got {j['title']!r}")
    check("url comes from 'hostedUrl' field", j["url"].startswith("https://jobs.lever.co/"), f"got {j['url']!r}")
    check("location is flat string from nested categories", isinstance(j["location"], str) and len(j["location"]) > 0,
          f"got {j['location']!r}")
    check("createdAt epoch-ms converted to ISO timestamp",
          j["posted_at"] and "T" in j["posted_at"] and "2024" in j["posted_at"],
          f"got {j['posted_at']!r}")

empty = with_fixture("lever_empty.json", fetch_jobs.fetch_lever, "empty-co")
check("empty list returns empty result", empty == [], f"got {empty}")

# Lever's parser checks isinstance(data, list); if API returns a dict the parser should return []
real = fetch_jobs.fetch_json
fetch_jobs.fetch_json = lambda url: {"error": "not a list"}
try:
    out = fetch_jobs.fetch_lever("any")
    check("non-list response returns [] (defensive)", out == [], f"got {out}")
finally:
    fetch_jobs.fetch_json = real


# ----------------------------------------------------------------------
# Ashby
# ----------------------------------------------------------------------
print("\nAshby:")
jobs = with_fixture("ashby_ramp.json", fetch_jobs.fetch_ashby, "Ramp")
check("happy fixture returns >= 2 jobs", len(jobs) >= 2, f"got {len(jobs)}")
if jobs:
    j = jobs[0]
    check("each job has expected keys",
          {"source", "company_slug", "title", "location", "url"} <= j.keys(),
          f"got keys {set(j.keys())}")
    check("source is tagged 'ashby'", j["source"] == "ashby", f"got {j['source']}")
    check("companyName from API is preferred over slug", j["company_name"] == "Ramp", f"got {j['company_name']!r}")
    check("location is a flat string", isinstance(j["location"], str), f"got {type(j['location']).__name__}")
    check("url comes from 'jobUrl' field", j["url"].startswith("https://jobs.ashbyhq.com/"), f"got {j['url']!r}")
    check("HTML in descriptionHtml is stripped", "<p>" not in j["description"] and "<" not in j["description"], f"got {j['description']!r}")
    # Salary range parsed from compensationTierSummary
    check("salary_range parses compensationTierSummary", "$220K" in j.get("salary_range", "") or "220K" in j.get("salary_range", ""),
          f"got {j.get('salary_range')!r}")

empty = with_fixture("ashby_empty.json", fetch_jobs.fetch_ashby, "empty-co")
check("empty board returns empty list", empty == [], f"got {empty}")


# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------
print()
print("=" * 40)
print(f"Result: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
