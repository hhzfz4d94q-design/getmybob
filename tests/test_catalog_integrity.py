"""Catalog integrity tests for healthtech_companies.json (and vc_portfolio_companies.json).

Guards against the bugs we shipped tonight:
  - duplicate entries (AKASA + Akasa)
  - invalid atsHint values (silently drop from scrape)
  - parenthesized names that produce broken slugs
  - missing or malformed slug field
  - HEALTHTECH_SET fuzz mismatch with companies actually in feed

Run via:  python3 tests/test_catalog_integrity.py
"""
import os
import sys
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fetch_jobs

PASS = 0
FAIL = 0
SCRAPABLE_ATS = {'greenhouse', 'lever', 'ashby', 'workable'}
KNOWN_ATS = SCRAPABLE_ATS | {'workday', 'google', 'amazon'}  # acceptable but not auto-scraped


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  ({detail})")


# ----- Healthtech catalog -----
print("healthtech_companies.json:\n")
path = os.path.join(ROOT, 'healthtech_companies.json')
check("file exists", os.path.exists(path), path)
data = json.load(open(path))
entries = data.get('companies', [])
check("has companies array", isinstance(entries, list) and len(entries) > 50, f"got {len(entries)}")

# Each entry has name + category + atsHint + slug
required_fields = ['name', 'category', 'atsHint', 'slug']
for i, e in enumerate(entries):
    for f in required_fields:
        if not isinstance(e, dict) or f not in e:
            check(f"entry {i} missing required field '{f}'", False, f"entry={e}")
            break

# Dedupe check — by canonical name
def canon(name):
    n = (name or '').lower()
    n = re.sub(r'\s*\([^)]*\)\s*$', '', n)
    n = re.sub(r',?\s*(inc|llc|corp|corporation|ltd|plc|co|company)\.?\s*$', '', n)
    n = re.sub(r'[^a-z0-9 ]+', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

canons = [canon(e['name']) for e in entries]
dupes = {c for c in canons if canons.count(c) > 1}
check("no duplicate companies (by canonical name)", len(dupes) == 0, f"dupes: {dupes}")

# All atsHints are known
bad_ats = [e['name'] for e in entries if e.get('atsHint') not in KNOWN_ATS]
check("all atsHint values are known", not bad_ats, f"bad: {bad_ats[:5]}")

# Slug format: lowercase alphanumeric + hyphens
SLUG_RX = re.compile(r'^[a-z0-9-]+$')
bad_slugs = [(e['name'], e['slug']) for e in entries if not SLUG_RX.match(e.get('slug', ''))]
check("all slugs match [a-z0-9-]+", not bad_slugs, f"bad: {bad_slugs[:5]}")

# Slugs don't have parenthesized cruft (no "amazon" suffix from "PillPack (Amazon)")
crufty = [(e['name'], e['slug']) for e in entries
          if '(' in e['name'] and not any(e['name'] == k for k in [
              'PillPack (Amazon)', 'Iora Health (One Medical)', 'Livongo (Teladoc)',
              'WW (Weight Watchers)', 'One Medical (Amazon)'
          ])]
# Just verify: parenthetical names have a slug that doesn't include the parenthetical
for name, slug in [(e['name'], e['slug']) for e in entries if '(' in e['name']]:
    paren = re.search(r'\(([^)]+)\)', name).group(1).lower().replace(' ', '-')
    if paren in slug:
        check(f"'{name}' slug contains parenthetical '{paren}'", False, f"slug={slug}")

# Scrapable entries have non-empty slugs
scrapable = [e for e in entries if e.get('atsHint') in SCRAPABLE_ATS]
check(f"scrapable entries ({len(scrapable)}) all have non-empty slug",
      all(e.get('slug') for e in scrapable), "some scrapable entries missing slug")

# Catalog loads into HEALTHTECH_SET correctly
from matcher import catalogs as _cat
_cat.load_healthtech_catalog()
fetch_jobs.HEALTHTECH_COMPANIES = _cat.HEALTHTECH_COMPANIES
fetch_jobs.HEALTHTECH_SET = _cat.HEALTHTECH_SET
check("HEALTHTECH_COMPANIES populated", len(fetch_jobs.HEALTHTECH_COMPANIES) == len(entries),
      f"in-mem {len(fetch_jobs.HEALTHTECH_COMPANIES)} vs file {len(entries)}")
check("HEALTHTECH_SET deduped (canonical form)",
      len(fetch_jobs.HEALTHTECH_SET) == len(set(canons)),
      f"set {len(fetch_jobs.HEALTHTECH_SET)} vs unique canons {len(set(canons))}")

# canonical_company spec test — round trip
check("canonical_company('Bio-Reference Laboratories') == 'bioreference laboratories'",
      fetch_jobs.canonical_company('Bio-Reference Laboratories') == 'bioreference laboratories')
check("canonical_company('BioReference') == 'bioreference'",
      fetch_jobs.canonical_company('BioReference') == 'bioreference')
check("canonical_company('Prescryptive Health, Inc.') == 'prescryptive health'",
      fetch_jobs.canonical_company('Prescryptive Health, Inc.') == 'prescryptive health')
check("canonical_company('PillPack (Amazon)') == 'pillpack'",
      fetch_jobs.canonical_company('PillPack (Amazon)') == 'pillpack')
check("canonical_company('') == ''",
      fetch_jobs.canonical_company('') == '')
check("canonical_company(None) == ''",
      fetch_jobs.canonical_company(None) == '')

# ----- VC portfolio catalog -----
print("\nvc_portfolio_companies.json:\n")
vc_path = os.path.join(ROOT, 'vc_portfolio_companies.json')
check("file exists", os.path.exists(vc_path))
vc_data = json.load(open(vc_path))
vc_entries = vc_data.get('companies', [])
check("has companies array", isinstance(vc_entries, list))
vc_canons = [canon(e.get('name', '')) for e in vc_entries]
vc_dupes = {c for c in vc_canons if vc_canons.count(c) > 1}
check("no duplicates in VC portfolio", len(vc_dupes) == 0, f"dupes: {vc_dupes}")

print()
print("=" * 40)
print(f"Result: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
