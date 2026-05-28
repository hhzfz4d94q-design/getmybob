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


# Phase 5: per-user target companies merger
def _merge_user_target_companies(companies):
    """Path 2: read each user's profile.targetCompanies (AI-suggested) and merge them
    into the in-memory companies dict so the scraper picks them up. No-op if no user
    profile has targetCompanies yet (e.g. before the Worker prompt is updated)."""
    try:
        users = load_users()
    except Exception as e:
        print(f"[user-targets] load_users failed: {e}", flush=True)
        return

    # Track what slugs/tenants already exist per ATS so we don't duplicate
    existing = {ats: set() for ats in ("greenhouse", "lever", "ashby")}
    existing["workday"] = set()
    for ats in ("greenhouse", "lever", "ashby"):
        for entry in companies.get(ats, []):
            if isinstance(entry, str):
                existing[ats].add(entry.lower())
            elif isinstance(entry, dict) and entry.get("slug"):
                existing[ats].add(entry["slug"].lower())
    for entry in companies.get("workday", []):
        if isinstance(entry, dict) and entry.get("tenant"):
            existing["workday"].add(entry["tenant"].lower())

    added = {ats: 0 for ats in ("greenhouse", "lever", "ashby")}
    skipped = 0

    for u in users:
        slug = (u.get("slug") if isinstance(u, dict) else u) or ""
        if not slug:
            continue
        try:
            profile = load_skills_profile(slug) or {}
        except Exception as e:
            print(f"[user-targets:{slug}] profile fetch failed: {e}", flush=True)
            continue

        targets = profile.get("targetCompanies") or []
        if not targets:
            continue

        user_industries = profile.get("industries", []) or []

        for t in targets:
            # Each target can be a dict {name, atsHint, why} or a bare string name
            if isinstance(t, str):
                name = t
                hint = "greenhouse"
            elif isinstance(t, dict):
                name = t.get("name") or t.get("slug") or ""
                hint = (t.get("atsHint") or t.get("ats") or "greenhouse").lower()
            else:
                continue
            if not name:
                continue

            target_slug = _slugify_company_name(t.get("slug") if isinstance(t, dict) and t.get("slug") else name)

            # Greenhouse/Lever/Ashby take a simple slug; Workday needs tenant+subdomain+site
            # which we now try to parse from an atsUrl the AI may have provided.
            if hint == "workday":
                ats_url = t.get("atsUrl") if isinstance(t, dict) else None
                wd_tenant = wd_subdomain = wd_site = None
                if ats_url:
                    # Parse https://{tenant}.{subdomain}.myworkdayjobs.com/{site}
                    wd_match = re.match(
                        r"https?://([^./]+)\.(wd\d+)\.myworkdayjobs\.com/([^/?#]+)",
                        ats_url,
                    )
                    if wd_match:
                        wd_tenant, wd_subdomain, wd_site = wd_match.groups()
                if not wd_tenant:
                    # Slice 3.5 fallback heuristic: AI didn't give us a usable atsUrl,
                    # but workday tenant slugs often follow a predictable pattern. Try
                    # the most common combo (wd1 + Careers/External) so the scraper
                    # gets a chance — it will fail gracefully if the slug is wrong.
                    wd_tenant = target_slug
                    wd_subdomain = "wd1"
                    wd_site = "Careers"
                    print(f"[user-targets:{slug}] workday fallback for '{name}' -> {wd_tenant}.{wd_subdomain}.myworkdayjobs.com/{wd_site} (no atsUrl from AI)", flush=True)
                wd_key = wd_tenant.lower()
                if wd_key in existing.setdefault("workday", set()):
                    continue
                companies.setdefault("workday", []).append({
                    "name": name,
                    "tenant": wd_tenant,
                    "subdomain": wd_subdomain,
                    "site": wd_site,
                    "industries": user_industries or DEFAULT_INDUSTRIES,
                    "_added_by_user": slug,
                })
                existing["workday"].add(wd_key)
                added.setdefault("workday", 0)
                added["workday"] += 1
                continue

            # Multi-ATS fallback (2026-05-27): the AI's atsHint is unreliable —
            # it defaults to "greenhouse" for ~half the suggestions even when
            # the company actually uses Lever/Ashby/WTTJ/Workable. So for any
            # slug-based hint (or "unknown"), we add the target_slug to ALL
            # four slug-based pools (greenhouse, lever, ashby, wttj). Each
            # scraper either returns jobs or silently 404s. Whichever wins
            # gives us coverage; we pay ~3 extra HTTP requests per company.
            # This is also how WTTJ gets activated for the first time — it
            # was coded but had 0 companies configured.
            SLUG_POOLS = ("greenhouse", "lever", "ashby", "wttj", "workable", "icims", "smartrecruiters", "pinpoint", "teamtailor", "recruitee", "wellfound", "trueup")
            if hint not in SLUG_POOLS and hint != "unknown":
                skipped += 1
                continue

            for pool in SLUG_POOLS:
                existing.setdefault(pool, set())
                if target_slug in existing[pool]:
                    continue
                entry = {
                    "slug": target_slug,
                    "industries": user_industries or DEFAULT_INDUSTRIES,
                    "_added_by_user": slug,
                    "_ai_hint": hint,  # debugging breadcrumb
                }
                if pool == "wttj":
                    entry["name"] = name
                companies.setdefault(pool, []).append(entry)
                existing[pool].add(target_slug)
                added.setdefault(pool, 0)
                added[pool] += 1

    total = sum(added.values())
    if total:
        print(f"[user-targets] merged {total} per-user companies (greenhouse={added.get('greenhouse',0)}, lever={added.get('lever',0)}, ashby={added.get('ashby',0)}, wttj={added.get('wttj',0)}, workday={added.get('workday',0)}); skipped {skipped} non-routable", flush=True)
    else:
        print(f"[user-targets] no targetCompanies in any user profile yet (Worker prompt may not be updated)", flush=True)
