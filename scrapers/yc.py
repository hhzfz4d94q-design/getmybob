"""ATS scraper for yc.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json


def fetch_yc(entry):
    """Y Combinator Work at a Startup. The site is an SPA — plain HTTP
    returns a shell. A separate workflow (scrape-yc.yml) uses Playwright
    to render the page daily and commits data/yc_jobs.json. We just read
    that snapshot here, no scraping. If the snapshot is missing or
    stale, we return [] gracefully."""
    snapshot_path = os.path.join(ROOT, "data", "yc_jobs.json")
    if not os.path.exists(snapshot_path):
        _dbg_to_file("yc", f"no snapshot at {snapshot_path} — run the scrape-yc workflow")
        return []
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        _dbg_to_file("yc", f"snapshot parse error: {e}")
        return []
    raw_jobs = data.get("jobs") or []
    meta = data.get("_meta") or {}
    scraped_at = meta.get("scrapedAt", "?")
    _dbg_to_file("yc", f"loaded {len(raw_jobs)} jobs from snapshot (scrapedAt={scraped_at})")
    out = []
    for j in raw_jobs:
        if not isinstance(j, dict):
            continue
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "YC Startup").strip()
        if not title:
            continue
        out.append({
            "source": "yc",
            "company_slug": company.lower().replace(" ", "-")[:40],
            "company_name": company[:80],
            "external_id": str(j.get("id") or j.get("url") or title),
            "title": title[:140],
            "location": (j.get("location") or "")[:200],
            "url": j.get("url") or "https://www.workatastartup.com/jobs",
            "posted_at": (j.get("posted_at") or "")[:10],
            "description": (j.get("description") or "")[:5000],
            "salary_range": "",
        })
    return out


