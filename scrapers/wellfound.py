"""ATS scraper for wellfound.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_wellfound(slug):
    """Wellfound (AngelList Talent) — startup-focused. Their public API was
    deprecated in 2023, but their public job-board pages embed jobs in
    __NEXT_DATA__ JSON we can scrape. Best-effort: many pages are now
    server-rendered behind auth."""
    url = f"https://wellfound.com/company/{slug}/jobs"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; getmemyjob/1.0; +https://getmemyjob.officebeatllc.com)",
            "Accept": "text/html"
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        try:
            os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
            with open(os.path.join(ROOT, "reports", "wellfound_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"[{slug}] fetch_failed: {type(e).__name__}: {e}\n")
        except Exception: pass
        return []
    # Extract __NEXT_DATA__ JSON
    import re as _r
    m = _r.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, _r.DOTALL)
    if not m:
        return []
    try:
        nd = json.loads(m.group(1))
    except Exception:
        return []
    # Walk the JSON looking for arrays of job-like objects
    out = []
    def _walk(node):
        if isinstance(node, list):
            for it in node: _walk(it)
        elif isinstance(node, dict):
            # Heuristic: job objects have "title" + "slug" + "company"
            if "title" in node and ("public_id" in node or "id" in node) and "compensation" in str(node):
                title = node.get("title") or ""
                if title and len(title) > 3 and len(title) < 200:
                    out.append({
                        "source": "wellfound",
                        "company_slug": slug,
                        "company_name": slug.replace("-", " ").title(),
                        "external_id": str(node.get("public_id") or node.get("id") or title),
                        "title": title,
                        "location": (node.get("locations") or [""])[0] if isinstance(node.get("locations"), list) else (node.get("location") or ""),
                        "url": f"https://wellfound.com/jobs/{node.get('public_id') or node.get('id')}",
                        "posted_at": node.get("posted_at") or "",
                        "description": _strip_html(node.get("description") or ""),
                        "salary_range": str(node.get("compensation") or ""),
                    })
            for v in node.values(): _walk(v)
    _walk(nd)
    # Dedupe by external_id
    seen = set(); deduped = []
    for j in out:
        if j["external_id"] in seen: continue
        seen.add(j["external_id"]); deduped.append(j)
    return deduped


