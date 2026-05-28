"""ATS scraper for icims.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json


def fetch_icims(entry):
    """iCIMS public-portal scraper. Most enterprise/banking deployments use
    careers-{slug}.icims.com. iCIMS doesn't expose a clean public JSON API,
    so we hit the all-jobs HTML page and extract job links via regex.
    Best-effort — pages with heavy JS rendering may return empty."""
    if isinstance(entry, dict):
        slug = entry.get("slug") or entry.get("tenant") or ""
    else:
        slug = entry or ""
    if not slug: return []
    base = f"https://careers-{slug}.icims.com"
    # The /jobs/search page returns a paginated list. searchPosition empty = all.
    page_html_url = f"{base}/jobs/search?ss=1&hashed=-1&searchKeyword=&searchLocation=&searchCategory=&searchPositionType=&mobile=false&width=1024&height=800&bga=true&needsRedirect=false&jan1offset=-300&jun1offset=-240"
    # fetch_json won't work for HTML; do raw HTTP
    try:
        req = urllib.request.Request(page_html_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; getmemyjob/1.0; +https://getmemyjob.officebeatllc.com)",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        # Log silently — many iCIMS portals are JS-rendered or block automated UA
        try:
            os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
            with open(os.path.join(ROOT, "reports", "icims_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"[{slug}] fetch_failed: {type(e).__name__}: {e}\n")
        except Exception: pass
        return []
    # Extract job links: <a href="/jobs/{id}/{slug-name}/job" ...>Title</a>
    import re as _r
    pattern = _r.compile(r'<a[^>]+href="(/jobs/(\d+)/[^"]+/job[^"]*)"[^>]*>([^<]+)</a>')
    out = []
    seen = set()
    for m in pattern.finditer(html):
        path, jid, title = m.group(1), m.group(2), m.group(3).strip()
        if jid in seen or not title: continue
        seen.add(jid)
        out.append({
            "source": "icims",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": jid,
            "title": title,
            "location": "",  # iCIMS list page doesn't include location reliably
            "url": base + path,
            "posted_at": "",
            "description": "",  # would require N+1 fetches to individual job pages — skip for now
            "salary_range": "",
        })
    if not out:
        try:
            os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
            with open(os.path.join(ROOT, "reports", "icims_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"[{slug}] 0 jobs found in HTML (len={len(html)}, likely JS-rendered)\n")
        except Exception: pass
    return out


