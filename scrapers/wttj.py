"""ATS scraper for wttj.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fetch_wttj(entry):
    """Welcome to the Jungle per-company scraper. Tries several extraction
    strategies in order of preference:
      1. __NEXT_DATA__ JSON blob (legacy Next.js pages)
      2. JSON-LD JobPosting schemas (SEO-required, almost always present)
      3. Embedded Remix/loader JSON
      4. Regex extraction of job-card links (last resort)
    Writes a one-line diagnostic to reports/wttj_debug.log so we can iterate
    when the structure changes."""
    if isinstance(entry, dict):
        slug = entry.get("slug") or ""
        name = entry.get("name") or slug
    elif isinstance(entry, str):
        slug = entry
        name = entry
    else:
        return []
    if not slug:
        return []

    def _dbg(msg):
        try:
            os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
            with open(os.path.join(ROOT, "reports", "wttj_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"[{slug}] {msg}\n")
        except Exception:
            pass

    # Try several endpoints in order. The public web pages are
    # Cloudflare-protected; api.welcometothejungle.com sometimes serves
    # the same data without the bot challenge.
    common_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    def _try(url):
        try:
            req = Request(url, headers=common_headers)
            with urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    _dbg(f"{url}: HTTP {resp.status}")
                    return None
                return resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            _dbg(f"{url}: {type(e).__name__}: {e}")
            return None

    # Phase 1: pull org metadata so we get the reference UUID
    org_html = _try(f"https://api.welcometothejungle.com/api/v1/organizations/{slug}")
    org_ref = None
    if org_html:
        try:
            org_data = json.loads(org_html)
            org_node = org_data.get("organization") or org_data
            if isinstance(org_node, dict):
                org_ref = org_node.get("reference")
                _dbg(f"resolved org.reference={org_ref!r}")
        except (json.JSONDecodeError, ValueError):
            pass

    # Phase 2: try jobs endpoints. Both slug-keyed and reference-UUID-keyed
    # variants since we don't know which the API prefers.
    keys_to_try = [slug]
    if org_ref and org_ref not in keys_to_try:
        keys_to_try.append(org_ref)
    html = None
    for key in keys_to_try:
        for shape in [
            f"https://api.welcometothejungle.com/api/v1/organizations/{key}/jobs",
            f"https://api.welcometothejungle.com/api/v1/organizations/{key}/job_offers",
            f"https://api.welcometothejungle.com/api/v1/organizations/{key}/job_postings",
            f"https://api.welcometothejungle.com/api/v1/profiles/{key}/jobs",
            f"https://api.welcometothejungle.com/api/v2/organizations/{key}/jobs",
        ]:
            html = _try(shape)
            if html:
                _dbg(f"OK jobs endpoint: {shape}")
                break
        if html:
            break
    if not html:
        # Last resort: bare org metadata (returned non-empty; we use it for
        # company description even though it has no jobs)
        html = org_html
        if html:
            _dbg("falling back to org metadata only (no jobs)")
    if not html:
        _dbg("all WTTJ candidates failed — likely Cloudflare bot protection")
        return []

    def _parsed_jobs_from_next_data():
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            return None
        page_props = ((data.get("props") or {}).get("pageProps") or {})
        for path_name, candidate in [
            ("pageProps.jobs", page_props.get("jobs")),
            ("pageProps.organization.jobs", (page_props.get("organization") or {}).get("jobs")),
            ("pageProps.company.jobs", (page_props.get("company") or {}).get("jobs")),
            ("pageProps.initialData.jobs", (page_props.get("initialData") or {}).get("jobs")),
            ("pageProps.results", page_props.get("results")),
        ]:
            if isinstance(candidate, list) and candidate:
                _dbg(f"matched NEXT_DATA path: {path_name} ({len(candidate)} jobs)")
                return candidate
        _dbg("NEXT_DATA found but no jobs at known paths")
        return None

    def _parsed_jobs_from_ldjson():
        items = []
        for raw in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                blob = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            queue = [blob] if not isinstance(blob, list) else list(blob)
            while queue:
                node = queue.pop()
                if isinstance(node, dict):
                    t = node.get("@type")
                    if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                        items.append(node)
                    for v in node.values():
                        if isinstance(v, (dict, list)):
                            queue.append(v)
                elif isinstance(node, list):
                    queue.extend(node)
        if items:
            _dbg(f"matched JSON-LD JobPostings: {len(items)} items")
            return items
        return None

    # If the response was raw JSON from api.welcometothejungle.com, try
    # to extract a jobs list. WTTJ's /organizations/{slug} endpoint returns
    # org metadata with the jobs nested somewhere — recursively scan all
    # arrays-of-dicts in the response and pick the one that looks like jobs.
    raw_jobs = None
    try:
        maybe_json = json.loads(html)
    except (json.JSONDecodeError, ValueError):
        maybe_json = None
    if maybe_json is not None:
        if isinstance(maybe_json, dict):
            _dbg(f"JSON top-level keys: {sorted(maybe_json.keys())[:30]}")
            org = maybe_json.get("organization") or maybe_json
            if isinstance(org, dict):
                _dbg(f"org keys: {sorted(org.keys())[:30]}")
                if "urls" in org:
                    _dbg(f"org.urls: {json.dumps(org['urls'])[:400]}")
                if "reference" in org:
                    _dbg(f"org.reference: {org['reference']!r}")
        # Recursively find arrays whose first element looks like a job
        def _looks_like_job(d):
            return (isinstance(d, dict) and
                    any(k in d for k in ("name","title","slug","position")) and
                    any(k in d for k in ("offices","locations","jobLocation","contract_type","reference","published_at")))
        def _find_jobs(node, depth=0):
            if depth > 8: return None
            if isinstance(node, list):
                if node and _looks_like_job(node[0]):
                    return node
                for item in node:
                    r = _find_jobs(item, depth+1)
                    if r: return r
            elif isinstance(node, dict):
                for v in node.values():
                    r = _find_jobs(v, depth+1)
                    if r: return r
            return None
        found = _find_jobs(maybe_json)
        if found:
            raw_jobs = found
            _dbg(f"recursive scan found {len(raw_jobs)} job-like records")
    if not raw_jobs:
        raw_jobs = _parsed_jobs_from_next_data() or _parsed_jobs_from_ldjson() or []
    if not raw_jobs:
        _dbg("NO jobs found via any strategy")
        return []

    out = []
    for j in raw_jobs:
        if not isinstance(j, dict):
            continue
        # Field names differ between strategies — accept either
        title = (j.get("name") or j.get("title") or "").strip()
        if not title:
            continue
        # URL
        if j.get("url"):
            job_url = j["url"]
        else:
            job_slug = j.get("slug") or j.get("reference") or ""
            job_url = f"https://www.welcometothejungle.com/en/companies/{slug}/jobs/{job_slug}" if job_slug else f"https://www.welcometothejungle.com/en/companies/{slug}/jobs"
        # Location
        loc_parts = []
        offices = j.get("offices") or j.get("locations") or []
        if isinstance(offices, list):
            for loc in offices:
                if isinstance(loc, dict):
                    lname = loc.get("name") or loc.get("city") or loc.get("addressLocality") or ""
                    if lname: loc_parts.append(lname)
        elif isinstance(offices, dict):
            lname = offices.get("name") or offices.get("addressLocality") or ""
            if lname: loc_parts.append(lname)
        # JobPosting JSON-LD uses jobLocation.address.addressLocality
        jl = j.get("jobLocation") or {}
        if isinstance(jl, dict):
            addr = jl.get("address") or {}
            if isinstance(addr, dict):
                ll = addr.get("addressLocality")
                if ll: loc_parts.append(ll)
        location_str = ", ".join(loc_parts)[:200]
        # Posted date
        posted_at = j.get("published_at") or j.get("created_at") or j.get("datePosted") or ""
        if posted_at and "T" in posted_at:
            posted_at = posted_at.split("T", 1)[0]
        desc_raw = j.get("description") or j.get("description_text") or ""
        out.append({
            "source": "wttj",
            "company_slug": slug,
            "company_name": name,
            "external_id": str(j.get("id") or j.get("identifier") or j.get("slug") or title),
            "title": title,
            "location": location_str,
            "url": job_url,
            "posted_at": posted_at[:10] if posted_at else "",
            "description": (desc_raw or "")[:5000],
            "salary_range": "",
        })
    _dbg(f"normalized {len(out)} jobs")
    return out


