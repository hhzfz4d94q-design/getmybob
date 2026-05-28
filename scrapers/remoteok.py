"""ATS scraper for remoteok.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json


def fetch_remoteok(entry):
    """Remote OK is a single-feed remote-jobs board. Public unauth JSON API
    returns ALL current jobs in one GET. We ignore the per-company `entry`
    argument and pull the full feed once. First element of the response is
    metadata; the rest are job records."""
    url = "https://remoteok.com/api"
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; getmemyjob/1.0; +https://getmemyjob.officebeatllc.com)",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=25) as resp:
            if resp.status != 200:
                return []
            raw = resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError):
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    seen_keys = set()
    for j in data:
        if not isinstance(j, dict):
            continue
        # First element is the legal/metadata blob; skip it
        if j.get("legal") and not j.get("position"):
            continue
        title = (j.get("position") or j.get("title") or "").strip()
        company = (j.get("company") or "").strip()
        if not title or not company:
            continue
        company_slug = (j.get("company_slug") or company).lower().replace(" ", "-")
        # The same role sometimes appears with multiple id formats — dedup on (slug, title)
        key = (company_slug, title.lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # URL
        job_url = j.get("apply_url") or j.get("url") or ""
        if job_url and not job_url.startswith("http"):
            job_url = "https://remoteok.com" + job_url
        # Location — Remote OK uses tags/location loosely
        loc = j.get("location") or "Remote"
        # Posted date
        posted_at = j.get("date") or j.get("epoch") or ""
        if isinstance(posted_at, str) and "T" in posted_at:
            posted_at = posted_at.split("T", 1)[0]
        elif isinstance(posted_at, (int, float)):
            # Epoch seconds → ISO date
            try:
                posted_at = datetime.fromtimestamp(int(posted_at), tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                posted_at = ""
        else:
            posted_at = str(posted_at)[:10] if posted_at else ""
        # Salary — Remote OK sometimes provides min/max
        salary = ""
        if j.get("salary_min") and j.get("salary_max"):
            salary = f"${int(j['salary_min']):,} - ${int(j['salary_max']):,}"
        elif j.get("salary_min"):
            salary = f"${int(j['salary_min']):,}+"
        out.append({
            "source": "remoteok",
            "company_slug": company_slug,
            "company_name": company,
            "external_id": str(j.get("id") or j.get("slug") or key),
            "title": title,
            "location": loc,
            "url": job_url,
            "posted_at": posted_at,
            "description": (j.get("description") or "")[:5000],
            "salary_range": salary,
        })
    return out


