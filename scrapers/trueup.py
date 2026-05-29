"""ATS scraper for trueup.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_trueup(entry):
    """Trueup.io tracks funded companies + has job feeds. They have a
    /jobs/api/v1 surface but rate-limited. Best-effort. Entry may be a
    slug or {slug, name}."""
    slug = entry if isinstance(entry, str) else entry.get("slug", "")
    if not slug: return []
    url = f"https://www.trueup.io/co/{slug}/jobs"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; getmemyjob/1.0)",
            "Accept": "text/html"
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    # Trueup pages embed __NEXT_DATA__ too
    import re as _r
    m = _r.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, _r.DOTALL)
    if not m: return []
    try:
        nd = json.loads(m.group(1))
    except Exception:
        return []
    out = []
    def _walk(node):
        if isinstance(node, list):
            for it in node: _walk(it)
        elif isinstance(node, dict):
            if "title" in node and "company" in str(node) and "location" in node:
                title = node.get("title") or ""
                if title and 3 < len(title) < 200:
                    out.append({
                        "source": "trueup",
                        "company_slug": slug,
                        "company_name": slug.replace("-", " ").title(),
                        "external_id": str(node.get("id") or node.get("slug") or title),
                        "title": title,
                        "location": node.get("location") or "",
                        "url": node.get("url") or node.get("apply_url") or "",
                        "posted_at": node.get("posted_at") or "",
                        "description": _strip_html(node.get("description") or ""),
                        "salary_range": str(node.get("salary") or ""),
                    })
            for v in node.values(): _walk(v)
    _walk(nd)
    seen = set(); deduped = []
    for j in out:
        if j["external_id"] in seen: continue
        seen.add(j["external_id"]); deduped.append(j)
    return deduped


