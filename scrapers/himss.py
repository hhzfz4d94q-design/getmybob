"""ATS scraper for himss.

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


def fetch_himss(entry):
    """HIMSS Career Center — niche healthcare-IT board. Their listings use
    Naylor's CareerSite platform under various subdomains. Try the public
    search RSS/HTML."""
    out = []
    # The HIMSS career site URL has changed forms over the years. Try the
    # most common current locations.
    candidates = [
        "https://jobmine.himss.org/jobs/rss",
        "https://jobmine.himss.org/jobs/",
        "https://careers.himss.org/jobs/rss",
        "https://careers.himss.org/jobs/",
    ]
    html = ""
    chosen = None
    for u in candidates:
        try:
            req = Request(u, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, text/html",
            })
            with urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    _dbg_to_file("himss", f"HTTP {resp.status} on {u}")
                    continue
                html = resp.read().decode("utf-8", errors="replace")
                chosen = u
                _dbg_to_file("himss", f"OK {u}: {len(html)} bytes")
                break
        except (HTTPError, URLError, TimeoutError) as e:
            _dbg_to_file("himss", f"{u}: {type(e).__name__}: {e}")
    if not html:
        _dbg_to_file("himss", "all HIMSS endpoints failed")
        return []
    # RSS path: <item><title>, <link>, <description>
    if chosen and chosen.endswith("/rss"):
        items = re.findall(r"<item>(.*?)</item>", html, re.S)
        _dbg_to_file("himss", f"RSS items found: {len(items)}")
        for it in items:
            title = re.search(r"<title>(?:<!\[CDATA\[)?([^<]+?)(?:\]\]>)?</title>", it)
            link = re.search(r"<link>([^<]+)</link>", it)
            desc = re.search(r"<description>(?:<!\[CDATA\[)?([^<]+?)(?:\]\]>)?</description>", it, re.S)
            pub = re.search(r"<pubDate>([^<]+)</pubDate>", it)
            if not (title and link):
                continue
            title_text = title.group(1).strip()
            # Many RSS feeds put "Title - Company" together
            if " - " in title_text:
                tname, company = title_text.rsplit(" - ", 1)
            else:
                tname, company = title_text, "Healthcare Employer"
            out.append({
                "source": "himss",
                "company_slug": company.lower().replace(" ", "-")[:40],
                "company_name": company[:80],
                "external_id": link.group(1).strip()[:80],
                "title": tname[:140],
                "location": "",
                "url": link.group(1).strip(),
                "posted_at": (pub.group(1).strip()[:10] if pub else ""),
                "description": (desc.group(1).strip() if desc else "")[:5000],
                "salary_range": "",
            })
    _dbg_to_file("himss", f"normalized {len(out)} jobs")
    return out


