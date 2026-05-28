"""Company catalog loaders + scrape-pool mergers.

Extracted from fetch_jobs.py 2026-05-28 (Phase 1 of split refactor).

Three catalogs feed the scrape pool:
  1. healthtech_companies.json (in-repo, curated HIT companies)
  2. vc_portfolio_companies.json (AI-discovered, weekly refresh)
  3. Per-user profile.targetCompanies (lives in worker — merged via separate path)

Each catalog has a loader (populates module globals) + a merger (adds the
catalog's companies to the scrape pool dict the scrapers iterate over).
"""
import json
import os
import re

from matcher.canonical import canonical_company

# Module globals — fetch_jobs.py re-imports these for backward compat
VC_PORTFOLIO_COMPANIES = []  # list of dicts {name, industry, fundingStage, atsHint}
HEALTHTECH_COMPANIES = []    # list of dicts {name, category, atsHint, slug}
HEALTHTECH_SET = set()       # CANONICAL company names for fast scoring lookup


def _root():
    """Resolve the repo root via this file's location (matcher/catalogs.py)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_healthtech_catalog(root=None):
    """Load curated healthtech catalog from healthtech_companies.json.
    Universal supplement to per-user targetCompanies. Adds healthcare IT
    breadth for users who target health/pharma/digital-health industries."""
    global HEALTHTECH_COMPANIES, HEALTHTECH_SET
    path = os.path.join(root or _root(), 'healthtech_companies.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        HEALTHTECH_COMPANIES = d.get('companies', []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
        HEALTHTECH_SET = set((c.get('name') or '').lower().strip() for c in HEALTHTECH_COMPANIES if isinstance(c, dict))
        print(f'[healthtech] loaded {len(HEALTHTECH_COMPANIES)} curated companies', flush=True)
    except FileNotFoundError:
        HEALTHTECH_COMPANIES = []
        HEALTHTECH_SET = set()
    except Exception as e:
        print(f'[healthtech] load failed: {e}', flush=True)
        HEALTHTECH_COMPANIES = []
        HEALTHTECH_SET = set()
    # Rebuild HEALTHTECH_SET to use canonical forms — fixes spelling-variation misses
    # ("Bio-Reference Laboratories" vs "BioReference" etc.)
    HEALTHTECH_SET = set(canonical_company(c.get('name')) for c in HEALTHTECH_COMPANIES if isinstance(c, dict))


def load_vc_portfolio(root=None):
    """Load discovered VC-portfolio companies from vc_portfolio_companies.json.
    Called once at startup. If file missing, returns empty list (no error)."""
    global VC_PORTFOLIO_COMPANIES
    path = os.path.join(root or _root(), 'vc_portfolio_companies.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        VC_PORTFOLIO_COMPANIES = d.get('companies', []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
        print(f'[vc-portfolio] loaded {len(VC_PORTFOLIO_COMPANIES)} discovered companies', flush=True)
    except FileNotFoundError:
        VC_PORTFOLIO_COMPANIES = []
    except Exception as e:
        print(f'[vc-portfolio] skipped: {e}', flush=True)
        VC_PORTFOLIO_COMPANIES = []


def merge_healthtech_catalog(companies):
    """Path 4: merge curated healthtech catalog companies into the scrape pool."""
    if not HEALTHTECH_COMPANIES:
        return
    existing = {ats: set() for ats in ('greenhouse', 'lever', 'ashby', 'workable')}
    for ats in existing:
        for entry in companies.get(ats, []):
            slug = entry if isinstance(entry, str) else (entry.get('slug') if isinstance(entry, dict) else '')
            if slug: existing[ats].add(slug.lower())
    added = 0
    for c in HEALTHTECH_COMPANIES:
        if not isinstance(c, dict): continue
        name = (c.get('name') or '').strip()
        if not name: continue
        ats = (c.get('atsHint') or 'greenhouse').strip().lower()
        if ats not in ('greenhouse', 'lever', 'ashby', 'workable'):
            continue
        if ats not in companies: companies[ats] = []
        slug = (c.get('slug') or '').strip().lower()
        if not slug:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        if not slug: continue
        if slug in existing.get(ats, set()): continue
        companies[ats].append(slug)
        existing.setdefault(ats, set()).add(slug)
        added += 1
    if added:
        print(f'[healthtech] merged {added} catalog companies into scrape pool', flush=True)


def merge_vc_portfolio_companies(companies):
    """Path 3: merge discovered VC-portfolio companies into the scrape pool."""
    if not VC_PORTFOLIO_COMPANIES:
        return
    existing = {ats: set() for ats in ('greenhouse', 'lever', 'ashby', 'workable')}
    for ats in existing:
        for entry in companies.get(ats, []):
            slug = entry if isinstance(entry, str) else (entry.get('slug') if isinstance(entry, dict) else '')
            if slug: existing[ats].add(slug.lower())
    added = 0
    for c in VC_PORTFOLIO_COMPANIES:
        name = (c.get('name') or '').strip() if isinstance(c, dict) else str(c).strip()
        if not name: continue
        ats = (c.get('atsHint') or 'greenhouse').strip().lower() if isinstance(c, dict) else 'greenhouse'
        if ats not in companies: companies[ats] = []
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        if not slug: continue
        if slug in existing.get(ats, set()): continue
        companies[ats].append(slug)
        existing.setdefault(ats, set()).add(slug)
        added += 1
    if added:
        print(f'[vc-portfolio] merged {added} discovered companies into scrape pool', flush=True)
