"""ATS scraper for healthecareers.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json

def _dbg_to_file(*args, **kwargs):
    """No-op stub — debug helper was lost during scraper extraction."""
    pass



def fetch_healthecareers(entry):
    """Health eCareers — healthcare-only job board with a public search page.
    Best-effort HTML scrape of the search results. Tries the JSON-LD
    JobPosting schemas embedded in each page (SEO-required)."""
    out = []
    # Focus on healthcare-IT and senior roles — Geetanjali's lane
    for query in ["healthcare-it", "informatics", "digital-health", "ehr"]:
        url = f"https://www.healthecareers.com/jobs?q={query}"
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html",
            })
            with urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    _dbg_to_file("healthecareers", f"HTTP {resp.status} on {url}")
                    continue
                html = resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            _dbg_to_file("healthecareers", f"fetch error on {query}: {type(e).__name__}: {e}")
            continue
        _dbg_to_file("healthecareers", f"OK {query}: {len(html)} bytes")
        seen_ids = set()
        for ld in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                blob = json.loads(ld)
            except (json.JSONDecodeError, ValueError):
                continue
            items = blob if isinstance(blob, list) else [blob]
            for j in items:
                if not isinstance(j, dict):
                    continue
                if j.get("@type") not in ("JobPosting", ["JobPosting"]):
                    continue
                title = (j.get("title") or "").strip()
                org = j.get("hiringOrganization") or {}
                company = (org.get("name") if isinstance(org, dict) else "") or "Healthcare Employer"
                if not title:
                    continue
                jid = str(j.get("identifier") or j.get("url") or title)
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)
                jl = j.get("jobLocation") or {}
                loc_name = ""
                if isinstance(jl, dict):
                    addr = jl.get("address") or {}
                    if isinstance(addr, dict):
                        loc_name = addr.get("addressLocality") or ""
                out.append({
                    "source": "healthecareers",
                    "company_slug": company.lower().replace(" ", "-")[:40],
                    "company_name": company[:80],
                    "external_id": jid[:80],
                    "title": title[:140],
                    "location": loc_name[:200],
                    "url": j.get("url") or url,
                    "posted_at": (j.get("datePosted") or "")[:10],
                    "description": (j.get("description") or "")[:5000],
                    "salary_range": "",
                })
    _dbg_to_file("healthecareers", f"normalized {len(out)} total jobs")
    return out


