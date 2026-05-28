"""ATS scraper for hn_hiring.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json

def _dbg_to_file(*args, **kwargs):
    """No-op stub — debug helper was lost during scraper extraction."""
    pass



def fetch_hn_hiring(entry):
    """Hacker News monthly 'Ask HN: Who is hiring?' thread. Use the Algolia
    HN API to find the latest thread, then fetch its tree to get all
    top-level comments — each is one job posting (best-effort parse)."""
    # 1. Find most recent 'Ask HN: Who is hiring?' story
    try:
        search = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=5"
        req = Request(search, headers={"User-Agent": "getmemyjob/1.0"})
        with urlopen(req, timeout=15) as resp:
            search_data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        _dbg_to_file("hn_hiring", f"search fail: {e}")
        return []
    hiring_id = None
    for h in search_data.get("hits", []):
        title = (h.get("title") or "").lower()
        if "who is hiring" in title or "who's hiring" in title:
            hiring_id = h.get("objectID")
            _dbg_to_file("hn_hiring", f"found thread: {h.get('title')} (id={hiring_id})")
            break
    if not hiring_id:
        _dbg_to_file("hn_hiring", "no Who-is-hiring thread found in recent search")
        return []
    # 2. Fetch the thread tree
    try:
        tree_url = f"https://hn.algolia.com/api/v1/items/{hiring_id}"
        req = Request(tree_url, headers={"User-Agent": "getmemyjob/1.0"})
        with urlopen(req, timeout=30) as resp:
            tree = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        _dbg_to_file("hn_hiring", f"tree fail: {e}")
        return []
    kids = tree.get("children") or []
    _dbg_to_file("hn_hiring", f"thread has {len(kids)} top-level comments")
    out = []
    for c in kids:
        if not isinstance(c, dict):
            continue
        text = c.get("text") or ""
        if not text or len(text) < 60:
            continue
        # First line of the comment is usually 'Company Name | Title | Location'
        # or 'Company Name (Location, Remote ok) ...' — best-effort parse.
        plain = re.sub(r"<[^>]+>", " ", text).strip()
        plain = re.sub(r"\s+", " ", plain)
        first_line = plain.split(".")[0][:400]
        # Try pipe-delimited first
        company = title = location = ""
        if " | " in first_line:
            parts = [p.strip() for p in first_line.split("|")]
            if len(parts) >= 2:
                company = parts[0]
                title = parts[1]
                location = parts[2] if len(parts) > 2 else ""
        if not company:
            # Match "Company Name (location) ..." pattern
            m2 = re.match(r"^([A-Z][A-Za-z0-9&.,\s]+?)\s*\(([^)]+)\)", first_line)
            if m2:
                company = m2.group(1).strip()
                location = m2.group(2).strip()
                # Title not clearly parsable — use the rest of the line
                title = first_line.split(")", 1)[1].strip(" -—:")[:100] or "Engineering role"
        if not company or not title:
            continue
        out.append({
            "source": "hn_hiring",
            "company_slug": company.lower().replace(" ", "-")[:40],
            "company_name": company[:80],
            "external_id": str(c.get("id")),
            "title": title[:140],
            "location": location[:200],
            "url": f"https://news.ycombinator.com/item?id={c.get('id')}",
            "posted_at": (c.get("created_at") or "")[:10],
            "description": plain[:5000],
            "salary_range": "",
        })
    _dbg_to_file("hn_hiring", f"normalized {len(out)} jobs from {len(kids)} comments")
    return out


