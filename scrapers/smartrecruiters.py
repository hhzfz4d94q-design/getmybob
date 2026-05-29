"""ATS scraper for smartrecruiters.

Extracted from fetch_jobs.py 2026-05-28 (Phase 4).
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from scrapers._http import fetch_json, _strip_html


def fetch_smartrecruiters(slug):
    """SmartRecruiters public posting API. Covers Bosch, GE, Visa, BlackRock,
    hundreds of mid-market firms. The API is well-documented and no auth needed
    for public postings."""
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
    data = fetch_json(url)
    if not data or "content" not in data:
        return []
    out = []
    for j in data.get("content", []):
        if not isinstance(j, dict): continue
        title = j.get("name") or ""
        if not title: continue
        loc = j.get("location") or {}
        loc_str = ""
        if isinstance(loc, dict):
            city = loc.get("city") or ""
            region = loc.get("region") or ""
            country = loc.get("country") or ""
            parts = [p for p in (city, region, country) if p]
            loc_str = ", ".join(parts)
            if loc.get("remote"):
                loc_str = (loc_str + " (Remote)") if loc_str else "Remote"
        elif isinstance(loc, str):
            loc_str = loc
        # Description: usually in jobAd.sections (multiple sections); concat
        desc_parts = []
        job_ad = j.get("jobAd") or {}
        sections = (job_ad.get("sections") or {})
        for key in ("jobDescription", "qualifications", "additionalInformation"):
            sec = sections.get(key) or {}
            txt = sec.get("text") if isinstance(sec, dict) else ""
            if txt:
                desc_parts.append(_strip_html(txt))
        desc = "\n\n".join(desc_parts)
        # Compensation if present
        sal_str = ""
        comp = j.get("typeOfEmployment") or {}
        if isinstance(comp, dict) and comp.get("label"):
            sal_str = comp.get("label", "")
        out.append({
            "source": "smartrecruiters",
            "company_slug": slug,
            "company_name": (j.get("company") or {}).get("name") or slug.replace("-", " ").title(),
            "external_id": str(j.get("id") or j.get("refNumber") or title),
            "title": title,
            "location": loc_str,
            "url": (j.get("ref") or "").replace("api.smartrecruiters.com/v1/companies", "jobs.smartrecruiters.com") or f"https://jobs.smartrecruiters.com/{slug}/{j.get('id', '')}",
            "posted_at": j.get("releasedDate") or j.get("createdOn") or "",
            "description": desc,
            "salary_range": sal_str,
        })
    return out


