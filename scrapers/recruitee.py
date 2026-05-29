"""ATS scraper for recruitee.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_recruitee(slug):
    """Recruitee ATS — EU scale-ups. Public job-board JSON-API."""
    url = f"https://{slug}.recruitee.com/api/offers/"
    data = fetch_json(url)
    if not data or "offers" not in data:
        return []
    out = []
    for j in data.get("offers", []):
        if not isinstance(j, dict): continue
        title = j.get("title") or j.get("position") or ""
        if not title: continue
        loc = j.get("location") or ""
        if isinstance(loc, str) and j.get("city"):
            loc = j.get("city") + (", " + j.get("country") if j.get("country") else "")
        out.append({
            "source": "recruitee",
            "company_slug": slug,
            "company_name": j.get("company_name") or slug.replace("-", " ").title(),
            "external_id": str(j.get("id") or j.get("slug") or title),
            "title": title,
            "location": loc,
            "url": j.get("careers_url") or j.get("url") or j.get("careers_apply_url") or "",
            "posted_at": j.get("created_at") or j.get("published_at") or "",
            "description": _strip_html(j.get("description") or j.get("requirements") or ""),
            "salary_range": j.get("salary") or "",
        })
    return out


