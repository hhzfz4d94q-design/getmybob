"""ATS scraper for lever.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json


def _extract_lever_salary(j):
    sr = j.get("salaryRange") or {}
    mn, mx = sr.get("min"), sr.get("max")
    if mn and mx:
        cur = (sr.get("currency") or "USD").upper()
        sym = "$" if cur == "USD" else (cur + " ")
        interval = sr.get("interval") or ""
        suffix = f" / {interval}" if interval and interval.lower() != "per-year-salary" else ""
        try:
            return f"{sym}{int(mn):,} - {sym}{int(mx):,}{suffix}"
        except Exception:
            return f"{sym}{mn} - {sym}{mx}{suffix}"
    desc = j.get("salaryDescription") or ""
    return _strip_html(desc)[:200]


def fetch_lever(slug):
    """Lever public job board API."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = fetch_json(url)
    if not isinstance(data, list):
        return []
    out = []
    for j in data:
        if not isinstance(j, dict):
            continue
        loc = ((j.get("categories") or {}).get("location")) or ""
        out.append({
            "source": "lever",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("text", ""),
            "location": loc,
            "url": j.get("hostedUrl", ""),
            "posted_at": (
                datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc).isoformat()
                if j.get("createdAt") else None
            ),
            "description": _strip_html(j.get("descriptionPlain") or j.get("description") or ""),
            "salary_range": _extract_lever_salary(j),
        })
    return out


