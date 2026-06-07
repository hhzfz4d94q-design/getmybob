"""ATS scraper for workday.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json


def fetch_workday(entry):
    """Workday Cxs API. Entry: {name, tenant, subdomain, site}.
    Pages through results (Workday paginates at 20 per request)."""
    if not isinstance(entry, dict):
        return []
    tenant = entry.get("tenant")
    sub = entry.get("subdomain", "wd1")
    site = entry.get("site")
    name = entry.get("name", tenant)
    if not (tenant and site):
        return []
    base = f"https://{tenant}.{sub}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    out = []
    offset = 0
    page_size = 20
    while offset < 200:  # cap at 200 jobs per company to be polite
        payload = {"appliedFacets": {}, "limit": page_size, "offset": offset, "searchText": ""}
        data = fetch_json(api, data=payload, method="POST", timeout=20)
        if not data or "jobPostings" not in data:
            break
        postings = data["jobPostings"]
        if not postings:
            break
        for j in postings:
            ext_path = j.get("externalPath") or ""
            url = f"{base}{ext_path}" if ext_path else ""
            out.append({
                "source": "workday",
                "company_slug": tenant,
                "company_name": name,
                "external_id": j.get("bulletFields", [None])[0] or ext_path or j.get("title"),
                "title": j.get("title", ""),
                "location": j.get("locationsText", "") or j.get("locations", ""),
                "url": url,
                "posted_at": j.get("postedOn", ""),
                "description": "",  # Workday requires a second API call per job for full description
                "salary_range": "",  # Workday salary requires per-job detail call; skip for now
            })
        offset += page_size
        if offset >= (data.get("total") or 0):
            break
        time.sleep(0.2)
    return out


