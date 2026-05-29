"""ATS scraper for pinpoint.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_pinpoint(slug):
    """Pinpoint ATS public job board API. Used by modern SaaS scale-ups."""
    # Pinpoint deployments are subdomain-style (e.g. companyname.pinpointhq.com)
    # Public job-board JSON endpoint:
    url = f"https://{slug}.pinpointhq.com/api/v1/jobs"
    data = fetch_json(url)
    if not data:
        # Try alt URL pattern
        url2 = f"https://www.pinpointhq.com/api/v1/job_boards/{slug}/jobs"
        data = fetch_json(url2)
        if not data:
            return []
    jobs = data if isinstance(data, list) else (data.get("data") or data.get("jobs") or [])
    out = []
    for j in jobs:
        if not isinstance(j, dict): continue
        attrs = j.get("attributes") or j
        title = attrs.get("title") or ""
        if not title: continue
        loc = attrs.get("location") or attrs.get("city") or ""
        if isinstance(loc, dict):
            loc = (loc.get("city") or "") + ", " + (loc.get("country") or "")
            loc = loc.strip(", ")
        out.append({
            "source": "pinpoint",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id") or attrs.get("id") or attrs.get("reference") or title),
            "title": title,
            "location": loc,
            "url": attrs.get("apply_url") or attrs.get("url") or attrs.get("post_url") or "",
            "posted_at": attrs.get("published_at") or attrs.get("created_at") or "",
            "description": _strip_html(attrs.get("description") or attrs.get("summary") or ""),
            "salary_range": attrs.get("salary") or "",
        })
    return out


