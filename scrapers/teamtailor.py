"""ATS scraper for teamtailor.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_teamtailor(slug):
    """TeamTailor ATS — EU/Nordic + US scale-ups. Public job-board JSON-API."""
    url = f"https://{slug}.teamtailor.com/jobs.json"
    data = fetch_json(url)
    if not data:
        # Alt: api.teamtailor.com
        data = fetch_json(f"https://api.teamtailor.com/v1/jobs?filter[company.slug]={slug}")
        if not data:
            return []
    jobs = data if isinstance(data, list) else (data.get("data") or data.get("jobs") or [])
    out = []
    for j in jobs:
        if not isinstance(j, dict): continue
        attrs = j.get("attributes") or j
        title = attrs.get("title") or ""
        if not title: continue
        loc_parts = []
        if attrs.get("city"): loc_parts.append(attrs["city"])
        if attrs.get("country"): loc_parts.append(attrs["country"])
        if attrs.get("remote-status") == "fully_remote" or attrs.get("remote_status") == "fully_remote":
            loc_parts.append("Remote")
        loc = ", ".join(loc_parts)
        url2 = ""
        links = j.get("links") or {}
        if isinstance(links, dict):
            url2 = links.get("careersite-job-url") or links.get("self") or ""
        out.append({
            "source": "teamtailor",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id") or attrs.get("reference") or title),
            "title": title,
            "location": loc,
            "url": url2,
            "posted_at": attrs.get("internal-name") and attrs.get("created-at") or attrs.get("created_at") or "",
            "description": _strip_html(attrs.get("body") or attrs.get("description") or ""),
            "salary_range": attrs.get("salary") or "",
        })
    return out


