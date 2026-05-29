"""ATS scraper for greenhouse.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def _extract_greenhouse_salary(j):
    # Look in metadata (custom fields) and pay_input_ranges
    pir = j.get("pay_input_ranges") or []
    if pir:
        try:
            r = pir[0]
            mn, mx = r.get("min_cents"), r.get("max_cents")
            cur = (r.get("currency_type") or "USD").upper()
            sym = "$" if cur == "USD" else (cur + " ")
            if mn and mx:
                return f"{sym}{mn//100:,} - {sym}{mx//100:,}"
        except Exception:
            pass
    for item in j.get("metadata") or []:
        name = (item.get("name") or "").lower()
        if any(k in name for k in ["salary", "pay range", "pay band", "compensation"]):
            val = item.get("value")
            if val:
                return str(val)[:200]
    return ""


def fetch_greenhouse(slug):
    """Greenhouse public job board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        if not isinstance(j, dict):
            continue  # defensively skip None / non-dict entries
        loc = (j.get("location") or {}).get("name") or ""
        out.append({
            "source": "greenhouse",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("absolute_url", ""),
            "posted_at": j.get("updated_at") or j.get("first_published"),
            "description": _strip_html((j.get("content") or "")),
            "salary_range": _extract_greenhouse_salary(j),
        })
    return out


