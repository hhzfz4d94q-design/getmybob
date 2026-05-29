"""ATS scraper for workable.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_workable(slug):
    """Workable public job board API. Most companies (incl. Resolver, ProcessUnity,
    many GRC SaaS) expose their open roles at apply.workable.com/{slug}.
    The widget endpoint returns JSON with all published jobs."""
    # Public widget endpoint — no auth required
    url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs?state=published&limit=200"
    data = fetch_json(url)
    if not data or "results" not in data:
        # Try alternate endpoint shapes some Workable deployments use
        alt = fetch_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
        if alt and "jobs" in alt:
            jobs_list = alt["jobs"]
        else:
            return []
    else:
        jobs_list = data["results"]
    out = []
    for j in jobs_list:
        if not isinstance(j, dict): continue
        title = j.get("title") or j.get("full_title") or ""
        if not title: continue
        loc = j.get("location") or {}
        loc_str = ""
        if isinstance(loc, dict):
            city = loc.get("city") or ""
            region = loc.get("region") or ""
            country = loc.get("country") or ""
            wp = loc.get("workplace_type") or ""
            parts = [p for p in (city, region, country) if p]
            loc_str = ", ".join(parts)
            if wp and wp.lower() in ("remote", "hybrid"):
                loc_str = (loc_str + f" ({wp})") if loc_str else wp
        elif isinstance(loc, str):
            loc_str = loc
        # Salary/compensation hint
        comp = j.get("compensation") or {}
        sal_str = ""
        if isinstance(comp, dict):
            mn = comp.get("min_amount") or comp.get("min")
            mx = comp.get("max_amount") or comp.get("max")
            cur = comp.get("currency") or "USD"
            if mn and mx:
                try:
                    sal_str = f"${int(mn):,} - ${int(mx):,}"
                except Exception:
                    sal_str = f"{mn} - {mx} {cur}"
        # Description: prefer full_description, fall back to description
        desc = _strip_html(j.get("full_description") or j.get("description") or "")
        out.append({
            "source": "workable",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id") or j.get("shortcode") or j.get("code") or title),
            "title": title,
            "location": loc_str,
            "url": j.get("application_url") or j.get("shortlink") or j.get("url") or "",
            "posted_at": j.get("published_on") or j.get("created_at") or "",
            "description": desc,
            "salary_range": sal_str,
        })
    return out


