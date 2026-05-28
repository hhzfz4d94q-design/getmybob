"""ATS scraper for ashby.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json


def _extract_ashby_salary(j):
    comp = j.get("compensation") or {}
    summary = comp.get("compensationTierSummary") or j.get("compensationTierSummary") or ""
    if summary:
        return _strip_html(summary)[:200]
    # Fall back to summary components if Ashby returns them
    components = comp.get("summaryComponents") or []
    parts = []
    for c in components:
        s = c.get("summary") or c.get("compensationType")
        if s:
            parts.append(str(s))
    return " · ".join(parts)[:200]


def fetch_ashby(slug):
    """Ashby public job board (HTML→JSON endpoint)."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        if not isinstance(j, dict):
            continue
        loc = j.get("location") or ""
        out.append({
            "source": "ashby",
            "company_slug": slug,
            "company_name": (data.get("companyName") or slug).replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("jobUrl", ""),
            "posted_at": j.get("publishedAt"),
            "description": _strip_html(j.get("descriptionHtml") or j.get("descriptionPlain") or ""),
            "salary_range": _extract_ashby_salary(j),
        })
    return out


