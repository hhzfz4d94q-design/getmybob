#!/usr/bin/env python3
"""
HealthTech Jobs Fetcher
-----------------------
Pulls open roles from Greenhouse, Lever, and Ashby ATS APIs for a curated
list of healthcare / health-tech companies. Stores them in a local SQLite
database, scores each job for relevance to a senior healthcare-IT leader,
and generates a single-file HTML dashboard.

No scraping — only public ATS APIs (legal + reliable).
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Ghost job threshold (days). Listings older than this are flagged as
# possibly not actively hiring.
GHOST_DAYS = 30

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "jobs.db")
COMPANIES_PATH = os.path.join(ROOT, "companies.json")
DASHBOARD_PATH = os.path.join(ROOT, "index.html")

# --- Profile-specific scoring (tuned for Geetanjali Arora) ---------------

# Senior leadership signal — title must contain at least one of these
SENIOR_TITLE_TERMS = [
    "vp", "vice president", "head of", "director", "sr director",
    "senior director", "principal", "chief", "lead", "executive"
]

# Healthcare-IT / digital transformation relevance — bonus points
RELEVANCE_TERMS = [
    "healthcare", "health", "clinical", "patient", "ehr", "emr",
    "digital transformation", "digital health", "product",
    "portfolio", "program", "platform", "saas", "ai", "agile",
    "scrum", "transformation", "operations", "delivery"
]

# Red flags — these subtract from score
SCAM_TERMS = [
    "earn from home", "make money", "no experience needed",
    "commission only", "100% remote opportunity!!!", "$$$",
    "work from anywhere worldwide"
]

# Staffing-agency / third-party recruiter giveaways
AGENCY_TERMS = [
    "our client", "client of ours", "leading client", "fortune 500 client",
    "contract to hire", "c2h", "w2 only", "1099 contract"
]

# Contract-employment signals — used to classify employment_type per job.
# Strong phrases unlikely to false-positive on full-time roles.
CONTRACT_STRONG_PHRASES = [
    "fractional", "interim",
    "1099", "c2c", "c2h", "w2 hourly",
    "consulting engagement", "contract role", "contract position",
    "contract-to-hire", "contract to hire",
    "fixed-term contract", "fixed term contract",
    "project-based engagement", "freelance",
    "12-month contract", "6-month contract", "3-month contract",
    "9-month contract", "18-month contract",
    "temporary contract", "temp contract",
]

# Title-only contract markers (more specific to avoid false positives)
CONTRACT_TITLE_MARKERS = [
    "fractional", "interim", "1099 ",
]

# Signals that indicate a permanent / full-time role
FULL_TIME_PHRASES = [
    "full-time", "full time", "permanent role", "permanent position",
    "401(k)", "401k", "stock options", "rsu", "vested over",
    "equity grant", "fully remote, full-time",
]


def detect_employment_type(job):
    """Return 'contract', 'full-time', or 'unknown' for a job."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    blob = title + " " + desc

    # Title-only contract markers — strong enough to classify on title alone
    for m in CONTRACT_TITLE_MARKERS:
        if m in title:
            return "contract"
    # Strong contract phrases anywhere
    for p in CONTRACT_STRONG_PHRASES:
        if p in blob:
            return "contract"
    # Otherwise, look for permanent / FTE signals
    for p in FULL_TIME_PHRASES:
        if p in blob:
            return "full-time"
    return "unknown"


# --- HTTP helpers --------------------------------------------------------

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HealthTechJobsFetcher/1.0"


def fetch_json(url, timeout=15, data=None, method=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = Request(url, headers=headers, data=body, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        return None
    except (URLError, TimeoutError):
        return None
    except Exception:
        return None


# --- ATS adapters --------------------------------------------------------

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


def _extract_lever_salary(j):
    sr = j.get("salaryRange") or {}
    mn, mx = sr.get("min"), sr.get("max")
    if mn and mx:
        cur = (sr.get("currency") or "USD").upper()
        sym = "$" if cur == "USD" else (cur + " ")
        interval = sr.get("interval") or ""
        suffix = f" / {interval}" if interval and interval.lower() != "per-year-salary" else ""
        try:
            return f"{sym}{int(mn):,} - {sym}{int(mx):,}{suffix}"
        except Exception:
            return f"{sym}{mn} - {sym}{mx}{suffix}"
    desc = j.get("salaryDescription") or ""
    return _strip_html(desc)[:200]


def fetch_lever(slug):
    """Lever public job board API."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = fetch_json(url)
    if not isinstance(data, list):
        return []
    out = []
    for j in data:
        loc = ((j.get("categories") or {}).get("location")) or ""
        out.append({
            "source": "lever",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("text", ""),
            "location": loc,
            "url": j.get("hostedUrl", ""),
            "posted_at": (
                datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc).isoformat()
                if j.get("createdAt") else None
            ),
            "description": _strip_html(j.get("descriptionPlain") or j.get("description") or ""),
            "salary_range": _extract_lever_salary(j),
        })
    return out


def _extract_ashby_salary(j):
    comp = j.get("compensation") or {}
    summary = comp.get("compensationTierSummary") or j.get("compensationTierSummary") or ""
    if summary:
        return _strip_html(summary)[:200]
    # Fall back to summary components if Ashby returns them
    components = comp.get("summaryComponents") or []
    parts = []
    for c in components:
        s = c.get("summary") or c.get("compensationType")
        if s:
            parts.append(str(s))
    return " · ".join(parts)[:200]


def fetch_ashby(slug):
    """Ashby public job board (HTML→JSON endpoint)."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        loc = j.get("location") or ""
        out.append({
            "source": "ashby",
            "company_slug": slug,
            "company_name": (data.get("companyName") or slug).replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("jobUrl", ""),
            "posted_at": j.get("publishedAt"),
            "description": _strip_html(j.get("descriptionHtml") or j.get("descriptionPlain") or ""),
            "salary_range": _extract_ashby_salary(j),
        })
    return out


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


def fetch_wttj(entry):
    """Welcome to the Jungle per-company scraper. Tries several extraction
    strategies in order of preference:
      1. __NEXT_DATA__ JSON blob (legacy Next.js pages)
      2. JSON-LD JobPosting schemas (SEO-required, almost always present)
      3. Embedded Remix/loader JSON
      4. Regex extraction of job-card links (last resort)
    Writes a one-line diagnostic to reports/wttj_debug.log so we can iterate
    when the structure changes."""
    if isinstance(entry, dict):
        slug = entry.get("slug") or ""
        name = entry.get("name") or slug
    elif isinstance(entry, str):
        slug = entry
        name = entry
    else:
        return []
    if not slug:
        return []

    def _dbg(msg):
        try:
            os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
            with open(os.path.join(ROOT, "reports", "wttj_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"[{slug}] {msg}\n")
        except Exception:
            pass

    # Try several endpoints in order. The public web pages are
    # Cloudflare-protected; api.welcometothejungle.com sometimes serves
    # the same data without the bot challenge.
    common_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    def _try(url):
        try:
            req = Request(url, headers=common_headers)
            with urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    _dbg(f"{url}: HTTP {resp.status}")
                    return None
                return resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            _dbg(f"{url}: {type(e).__name__}: {e}")
            return None

    # Phase 1: pull org metadata so we get the reference UUID
    org_html = _try(f"https://api.welcometothejungle.com/api/v1/organizations/{slug}")
    org_ref = None
    if org_html:
        try:
            org_data = json.loads(org_html)
            org_node = org_data.get("organization") or org_data
            if isinstance(org_node, dict):
                org_ref = org_node.get("reference")
                _dbg(f"resolved org.reference={org_ref!r}")
        except (json.JSONDecodeError, ValueError):
            pass

    # Phase 2: try jobs endpoints. Both slug-keyed and reference-UUID-keyed
    # variants since we don't know which the API prefers.
    keys_to_try = [slug]
    if org_ref and org_ref not in keys_to_try:
        keys_to_try.append(org_ref)
    html = None
    for key in keys_to_try:
        for shape in [
            f"https://api.welcometothejungle.com/api/v1/organizations/{key}/jobs",
            f"https://api.welcometothejungle.com/api/v1/organizations/{key}/job_offers",
            f"https://api.welcometothejungle.com/api/v1/organizations/{key}/job_postings",
            f"https://api.welcometothejungle.com/api/v1/profiles/{key}/jobs",
            f"https://api.welcometothejungle.com/api/v2/organizations/{key}/jobs",
        ]:
            html = _try(shape)
            if html:
                _dbg(f"OK jobs endpoint: {shape}")
                break
        if html:
            break
    if not html:
        # Last resort: bare org metadata (returned non-empty; we use it for
        # company description even though it has no jobs)
        html = org_html
        if html:
            _dbg("falling back to org metadata only (no jobs)")
    if not html:
        _dbg("all WTTJ candidates failed — likely Cloudflare bot protection")
        return []

    def _parsed_jobs_from_next_data():
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            return None
        page_props = ((data.get("props") or {}).get("pageProps") or {})
        for path_name, candidate in [
            ("pageProps.jobs", page_props.get("jobs")),
            ("pageProps.organization.jobs", (page_props.get("organization") or {}).get("jobs")),
            ("pageProps.company.jobs", (page_props.get("company") or {}).get("jobs")),
            ("pageProps.initialData.jobs", (page_props.get("initialData") or {}).get("jobs")),
            ("pageProps.results", page_props.get("results")),
        ]:
            if isinstance(candidate, list) and candidate:
                _dbg(f"matched NEXT_DATA path: {path_name} ({len(candidate)} jobs)")
                return candidate
        _dbg("NEXT_DATA found but no jobs at known paths")
        return None

    def _parsed_jobs_from_ldjson():
        items = []
        for raw in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                blob = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            queue = [blob] if not isinstance(blob, list) else list(blob)
            while queue:
                node = queue.pop()
                if isinstance(node, dict):
                    t = node.get("@type")
                    if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                        items.append(node)
                    for v in node.values():
                        if isinstance(v, (dict, list)):
                            queue.append(v)
                elif isinstance(node, list):
                    queue.extend(node)
        if items:
            _dbg(f"matched JSON-LD JobPostings: {len(items)} items")
            return items
        return None

    # If the response was raw JSON from api.welcometothejungle.com, try
    # to extract a jobs list. WTTJ's /organizations/{slug} endpoint returns
    # org metadata with the jobs nested somewhere — recursively scan all
    # arrays-of-dicts in the response and pick the one that looks like jobs.
    raw_jobs = None
    try:
        maybe_json = json.loads(html)
    except (json.JSONDecodeError, ValueError):
        maybe_json = None
    if maybe_json is not None:
        if isinstance(maybe_json, dict):
            _dbg(f"JSON top-level keys: {sorted(maybe_json.keys())[:30]}")
            org = maybe_json.get("organization") or maybe_json
            if isinstance(org, dict):
                _dbg(f"org keys: {sorted(org.keys())[:30]}")
                if "urls" in org:
                    _dbg(f"org.urls: {json.dumps(org['urls'])[:400]}")
                if "reference" in org:
                    _dbg(f"org.reference: {org['reference']!r}")
        # Recursively find arrays whose first element looks like a job
        def _looks_like_job(d):
            return (isinstance(d, dict) and
                    any(k in d for k in ("name","title","slug","position")) and
                    any(k in d for k in ("offices","locations","jobLocation","contract_type","reference","published_at")))
        def _find_jobs(node, depth=0):
            if depth > 8: return None
            if isinstance(node, list):
                if node and _looks_like_job(node[0]):
                    return node
                for item in node:
                    r = _find_jobs(item, depth+1)
                    if r: return r
            elif isinstance(node, dict):
                for v in node.values():
                    r = _find_jobs(v, depth+1)
                    if r: return r
            return None
        found = _find_jobs(maybe_json)
        if found:
            raw_jobs = found
            _dbg(f"recursive scan found {len(raw_jobs)} job-like records")
    if not raw_jobs:
        raw_jobs = _parsed_jobs_from_next_data() or _parsed_jobs_from_ldjson() or []
    if not raw_jobs:
        _dbg("NO jobs found via any strategy")
        return []

    out = []
    for j in raw_jobs:
        if not isinstance(j, dict):
            continue
        # Field names differ between strategies — accept either
        title = (j.get("name") or j.get("title") or "").strip()
        if not title:
            continue
        # URL
        if j.get("url"):
            job_url = j["url"]
        else:
            job_slug = j.get("slug") or j.get("reference") or ""
            job_url = f"https://www.welcometothejungle.com/en/companies/{slug}/jobs/{job_slug}" if job_slug else url
        # Location
        loc_parts = []
        offices = j.get("offices") or j.get("locations") or []
        if isinstance(offices, list):
            for loc in offices:
                if isinstance(loc, dict):
                    lname = loc.get("name") or loc.get("city") or loc.get("addressLocality") or ""
                    if lname: loc_parts.append(lname)
        elif isinstance(offices, dict):
            lname = offices.get("name") or offices.get("addressLocality") or ""
            if lname: loc_parts.append(lname)
        # JobPosting JSON-LD uses jobLocation.address.addressLocality
        jl = j.get("jobLocation") or {}
        if isinstance(jl, dict):
            addr = jl.get("address") or {}
            if isinstance(addr, dict):
                ll = addr.get("addressLocality")
                if ll: loc_parts.append(ll)
        location_str = ", ".join(loc_parts)[:200]
        # Posted date
        posted_at = j.get("published_at") or j.get("created_at") or j.get("datePosted") or ""
        if posted_at and "T" in posted_at:
            posted_at = posted_at.split("T", 1)[0]
        desc_raw = j.get("description") or j.get("description_text") or ""
        out.append({
            "source": "wttj",
            "company_slug": slug,
            "company_name": name,
            "external_id": str(j.get("id") or j.get("identifier") or j.get("slug") or title),
            "title": title,
            "location": location_str,
            "url": job_url,
            "posted_at": posted_at[:10] if posted_at else "",
            "description": (desc_raw or "")[:5000],
            "salary_range": "",
        })
    _dbg(f"normalized {len(out)} jobs")
    return out



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


def _dbg_to_file(source_key, msg):
    """Write a diagnostic line to reports/{source}_debug.log so we can
    iterate on these scrapers when their HTML/JSON changes."""
    try:
        os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
        with open(os.path.join(ROOT, "reports", f"{source_key}_debug.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def fetch_yc(entry):
    """Y Combinator Work at a Startup. The site is an SPA — plain HTTP
    returns a shell. A separate workflow (scrape-yc.yml) uses Playwright
    to render the page daily and commits data/yc_jobs.json. We just read
    that snapshot here, no scraping. If the snapshot is missing or
    stale, we return [] gracefully."""
    snapshot_path = os.path.join(ROOT, "data", "yc_jobs.json")
    if not os.path.exists(snapshot_path):
        _dbg_to_file("yc", f"no snapshot at {snapshot_path} — run the scrape-yc workflow")
        return []
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        _dbg_to_file("yc", f"snapshot parse error: {e}")
        return []
    raw_jobs = data.get("jobs") or []
    meta = data.get("_meta") or {}
    scraped_at = meta.get("scrapedAt", "?")
    _dbg_to_file("yc", f"loaded {len(raw_jobs)} jobs from snapshot (scrapedAt={scraped_at})")
    out = []
    for j in raw_jobs:
        if not isinstance(j, dict):
            continue
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "YC Startup").strip()
        if not title:
            continue
        out.append({
            "source": "yc",
            "company_slug": company.lower().replace(" ", "-")[:40],
            "company_name": company[:80],
            "external_id": str(j.get("id") or j.get("url") or title),
            "title": title[:140],
            "location": (j.get("location") or "")[:200],
            "url": j.get("url") or "https://www.workatastartup.com/jobs",
            "posted_at": (j.get("posted_at") or "")[:10],
            "description": (j.get("description") or "")[:5000],
            "salary_range": "",
        })
    return out



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


def fetch_healthecareers(entry):
    """Health eCareers — healthcare-only job board with a public search page.
    Best-effort HTML scrape of the search results. Tries the JSON-LD
    JobPosting schemas embedded in each page (SEO-required)."""
    out = []
    # Focus on healthcare-IT and senior roles — Geetanjali's lane
    for query in ["healthcare-it", "informatics", "digital-health", "ehr"]:
        url = f"https://www.healthecareers.com/jobs?q={query}"
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html",
            })
            with urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    _dbg_to_file("healthecareers", f"HTTP {resp.status} on {url}")
                    continue
                html = resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            _dbg_to_file("healthecareers", f"fetch error on {query}: {type(e).__name__}: {e}")
            continue
        _dbg_to_file("healthecareers", f"OK {query}: {len(html)} bytes")
        seen_ids = set()
        for ld in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
            try:
                blob = json.loads(ld)
            except (json.JSONDecodeError, ValueError):
                continue
            items = blob if isinstance(blob, list) else [blob]
            for j in items:
                if not isinstance(j, dict):
                    continue
                if j.get("@type") not in ("JobPosting", ["JobPosting"]):
                    continue
                title = (j.get("title") or "").strip()
                org = j.get("hiringOrganization") or {}
                company = (org.get("name") if isinstance(org, dict) else "") or "Healthcare Employer"
                if not title:
                    continue
                jid = str(j.get("identifier") or j.get("url") or title)
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)
                jl = j.get("jobLocation") or {}
                loc_name = ""
                if isinstance(jl, dict):
                    addr = jl.get("address") or {}
                    if isinstance(addr, dict):
                        loc_name = addr.get("addressLocality") or ""
                out.append({
                    "source": "healthecareers",
                    "company_slug": company.lower().replace(" ", "-")[:40],
                    "company_name": company[:80],
                    "external_id": jid[:80],
                    "title": title[:140],
                    "location": loc_name[:200],
                    "url": j.get("url") or url,
                    "posted_at": (j.get("datePosted") or "")[:10],
                    "description": (j.get("description") or "")[:5000],
                    "salary_range": "",
                })
    _dbg_to_file("healthecareers", f"normalized {len(out)} total jobs")
    return out


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


SOURCES = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby, "workday": fetch_workday, "wttj": fetch_wttj, "remoteok": fetch_remoteok, "yc": fetch_yc, "hn_hiring": fetch_hn_hiring, "healthecareers": fetch_healthecareers, "himss": fetch_himss}


# --- Utilities -----------------------------------------------------------

def _strip_html(s):
    import html as _html_mod
    s = s or ""
    # Some sources pre-encode entities (&lt;p&gt;…). Decode first so the regex catches tags.
    s = _html_mod.unescape(_html_mod.unescape(s))
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:4000]


STOP_WORDS = {"of", "the", "and", "for", "a", "an", "to", "with", "in", "on", "at", "by", "or"}


# Titles that look healthcare-y but aren't a fit for Geetanjali's profile
# (senior product / digital transformation / IT in healthcare — NOT a clinician,
# pharmacist, nurse, medical affairs, or pure sales/marketing role).
IRRELEVANT_TITLE_TERMS = [
    # Clinical practice roles (not IT/product)
    "clinical trial", "clinical research", "clinical operations",
    "clinical success", "clinical quality", "clinical educator",
    "clinical pharmacist", "clinical psychologist", "clinical specialist",
    "clinical lead", "clinical excellence", "clinical education",
    "clinical informatics nurse",
    # Healthcare practitioners
    "pharmacy", "pharmacist", "nursing", "nurse practitioner",
    "registered nurse", "physician", "psychiatrist", "psychologist",
    "social worker", "behavioral therapist", "case manager",
    "care coordinator", "care manager", "therapist",
    "physical therapist", "occupational therapist", "dietitian",
    "respiratory therapist",
    # Medical affairs (separate from product/IT)
    "medical affairs", "medical director", "medical writer",
    "medical science liaison",
    # Pure sales — Geetanjali is product/IT, NOT a sales/BD/GTM leader
    "director of sales", "head of sales", "vp of sales",
    "vice president of sales", "vice president, sales",
    "sales director", "regional sales manager", "enterprise sales",
    "account executive", "account manager", "inside sales",
    "sales lead", "sales engineer", "sales operations",
    "sales enablement", "revenue enablement", "head of revenue",
    "head of partnerships", "partnerships lead", "partnership lead",
    "business development lead", "business development manager",
    "business development representative", "bdr", "sdr",
    "head of growth", "growth lead", "growth marketing",
    "lead generation", "demand generation", "field sales",
    "channel sales", "commercial lead", "commercial director",
    "head of commercial", "vp commercial",
    # Marketing (different focus from product)
    "marketing director", "head of marketing", "vp of marketing",
    "vp, marketing", "marketing manager", "marketing lead",
    "product marketing", "brand marketing", "content marketing",
    "performance marketing", "marketing operations",
    "community manager", "community lead", "social media",
    # Customer support / care ops (not Geetanjali's profile)
    "customer success", "customer care", "customer support",
    "customer experience", "client success", "client services",
    # HR / Talent / People
    "talent acquisition", "talent partner", "talent operations",
    "recruiter", "people operations", "people partner",
    "head of people", "vp people", "people business partner",
    # Finance / Pricing / Ops (non-product)
    "pricing", "pricing strategy", "financial analyst",
    "fp&a", "controller", "treasurer", "tax manager",
    "general counsel", "compliance officer", "chief financial officer",
    "human resources",
    # Engineering IC roles (she's a program/product leader, not a hands-on engineer)
    "software engineer", "data engineer", "data scientist", "data science",
    "machine learning engineer", "ml engineer", "ai engineer",
    "devops engineer", "site reliability", "backend engineer",
    "frontend engineer", "full stack engineer", "qa engineer",
    "security engineer", "platform engineer",
    # Design roles (different discipline from product management)
    "product design", "ux design", "ui design", "design lead",
    "head of design", "vp design", "design director", "creative director",
    # Research / clinical research (academic / lab, not IT)
    "clinical research", "clinical experience", "translational research",
    "research scientist", "research director", "research fellow",
    # GTM / Go-to-market (sales/marketing function)
    "gtm", "go-to-market", "go to market",
    # Government / policy / regulatory affairs (separate function)
    "government affairs", "federal affairs", "regulatory affairs",
    "public policy", "policy director", "policy lead",
    # HR / Talent (bare "talent" catches "Head of Talent" etc.)
    "head of talent", "vp talent", "director of talent", "chief people officer",
    "people experience", "talent management",
    # Risk / Audit / Privacy / Legal compliance (not Geetanjali's lane)
    "risk officer", "head of risk", "internal audit", "privacy officer",
    "security officer", "chief information security",
    # Generic IC analyst roles
    "data analyst", "business analyst i", "research analyst",
    # Strategic initiatives / partnerships (community-y BD)
    "head of strategic initiatives", "strategic initiatives",
    "partnerships & community", "community lead",
    "head of community", "vp community",
    # Member / patient growth / engagement (marketing-flavoured)
    "member growth", "head of member", "member engagement",
    "patient growth", "patient marketing", "provider marketing",
    "user growth", "user acquisition",
    # Member / provider services (operational support)
    "member services", "provider services", "member experience",
    # Clinical documentation / coding (specialist, not product)
    "clinical documentation", "documentation integrity",
    "clinical coding", "medical coding", "icd",
    # Customer engineering / sales engineering
    "customer engineering", "solution engineering", "solutions engineer",
    "implementation engineer",
    # InfoSec / chief of staff
    "information security", "chief information security",
    "security architect", "security analyst", "vp of information",
    "chief of staff", "executive assistant", "executive coordinator",
    # Strategic ops at non-product orgs (too generic)
    "strategic operations", "field operations", "operations associate",
    # IT-security (her core IS healthcare-IT, but pure IT/Sec is too narrow)
    "it & security", "it and security", "it security",
    "it operations", "system administrator", "sysadmin",
    # Misc HR / talent variations
    "talent strategy", "talent program", "head of recruiting",
    "director of recruiting",
    # Strategic accounts / partnerships sales (sales-adjacent)
    "strategic account", "strategic accounts", "account director",
    "key account", "named accounts", "enterprise accounts",
    "strategic partnerships", "channel partnerships",
    "payor partnerships", "payer partnerships",
    "vp partnerships", "vp, partnerships",
    "director, partnerships", "director of partnerships",
    "bd lead", "bd director",
    # Revenue ops / biz ops (sales-adjacent functions)
    "revenue operations", "rev ops", "biz ops",
    "business operations", "business operations -", "business operations,",
    "deal desk", "deal operations",
    # Procurement / finance / accounting / audit
    "controller", "treasurer", "tax director",
    "chief accounting", "head of accounting",
    # Medical / clinical operations / informatics (specialist clinical IT)
    "medical excellence", "medical operations",
    "clinical ops", "clinical analytics", "clinical informatics",
    "clinical product", "clinical solutions",
    # Data engineering / architecture
    "data architect", "data solutions", "data engineering",
    "solutions architect", "enterprise architect",
    # Application / IT operations / support
    "application support", "application operations",
    "service desk", "help desk", "desktop support",
    # GRC / risk / governance
    "grc", "governance, risk", "governance risk", "risk management",
    "internal controls", "model risk",
    # Internal comms / brand / pr (now also caught by bare "communications")
    "head of brand", "brand director",
    "public relations", "investor relations", "ir lead",
    # Specialty insurance / product solutions (insurance product mgmt is its own world)
    "insurance product solutions",
    # Client / patient engagement (sales-side or care-team)
    "client engagement", "client services", "client success",
    "client partner", "patient engagement", "patient experience",
    # Talent community (recruiting funnel — not a real role)
    "talent community", "talent pool",
    # Coach / counsellor / specialist (clinician-flavoured)
    "mental health coach", "online coach", "online mental",
    "wellness coach", "health coach", "behavioral coach",
    "career coach",
    # Clinical-trial site / regulatory affairs niche
    "site start up", "site start-up", "study start up", "study start-up",
    "site activation", "clinical site",
    # Engineering management (line-managing engineers, not Geetanjali's lane)
    "engineering manager", "manager, engineering",
    "engineering team lead", "head of platform engineering",
    "adoption and value realization", "adoption manager",
    "value realization",
    # Manufacturing / production / lab ops
    "production operations", "manufacturing", "lab operations",
    "laboratory operations", "process development", "qa manager",
    "quality assurance manager", "facilities", "facility manager",
    # Generic IC analyst roles
    "data analyst", "business analyst i", "research analyst",
    # Junior / entry
    "junior", "intern", "internship", "associate ", "coordinator",
    "specialist i", "analyst i", "level i",
]


# Single tokens that should match on word boundary only (so "sales" doesn't catch "salesforce")
SINGLE_WORD_FILTERS = [
    "sales", "marketing", "recruiting", "recruiter", "staffing",
    "clinician", "underwriter", "underwriting", "auditor",
    "procurement", "communications", "comms",
    "security",  # info-sec / GRC roles — Geetanjali is product/transformation, not InfoSec
    "regulatory",  # regulatory affairs — clinical-research adjacent
    "supervisor",  # too junior
    "coach",  # health coaches, wellness coaches — non-IT roles
    "neuroscience",  # bench/lab research
    "materials",  # supply-chain / procurement
]


def _is_irrelevant_title(title):
    t = (title or "").lower()
    if any(term in t for term in IRRELEVANT_TITLE_TERMS):
        return True
    # Word-boundary check for single-word filters
    for w in SINGLE_WORD_FILTERS:
        if re.search(r"\b" + re.escape(w) + r"\b", t):
            return True
    return False


# --- Positive title whitelist (Phase 4) -------------------------------
# Universal themes for senior healthcare-IT / digital-transformation / product
# leaders. A title MUST contain at least one of these (or a keyword from the
# skills profile) to be shown. This converts the dashboard from a blacklist
# model ("hide bad") to a whitelist model ("only show relevant").
POSITIVE_TITLE_THEMES = [
    # Product / portfolio
    "product", "portfolio", "platform",
    # Transformation / innovation / digital
    "transformation", "innovation", "digital", "modernization", "automation",
    # AI / ML / data product
    "ai", "artificial intelligence", "machine learning", "ml", "data product",
    # Implementation / delivery / enterprise programs
    "implementation", "deployment", "enterprise", "delivery",
    # Strategy + senior titles (typically real C-suite / VP roles)
    "strategy", "strategist", "officer", "chief", "general manager", "gm",
    # Healthcare-IT specifics
    "ehr", "emr", "saas", "health it", "health tech", "healthtech",
    "interoperability", "informatics",
    # Engineering leadership (very senior, not IC)
    "head of engineering", "vp engineering", "vp of engineering",
    "chief technology", "cto", "cio", "ciso", "cdo", "cpo",
    # Operations leadership (when not blacklisted as "strategic operations" etc.)
    "vp operations", "vp of operations", "head of operations",
    # Programs / portfolio (her core)
    "program management", "head of program", "vp programs", "vp of programs",
    "head of portfolio", "vp portfolio", "head of programs",
    # Finance / banking / fintech (added Slice B v2 so bank/fintech employers
    # actually surface relevant senior roles instead of being silently dropped
    # by a healthcare-only theme list).
    "finance", "financial", "banking", "investment", "investments", "wealth",
    "treasury", "trading", "trader", "lending", "credit", "underwriting",
    "compliance", "risk", "audit", "regulatory", "fintech", "payments",
    "asset management", "capital markets", "private banking",
    "investment banking", "wealth management", "portfolio management",
    "managing director", "principal", "head of risk",
]


_POSITIVE_THEME_RE = None

def _build_positive_re():
    """Build a word-boundary regex from POSITIVE_TITLE_THEMES so substring bleed-through
    ('cto' matching 'director', 'product' matching 'production') is impossible."""
    global _POSITIVE_THEME_RE
    parts = []
    for theme in POSITIVE_TITLE_THEMES:
        # Allow flexible whitespace inside multi-word themes
        escaped = re.escape(theme).replace(r"\ ", r"\s+")
        parts.append(r"\b" + escaped + r"\b")
    _POSITIVE_THEME_RE = re.compile("|".join(parts), re.I)


# === Universal "never relevant" titles =====================================
# Bank back-office, IC engineering, pre-sales field roles, content production.
# Categories no user on this platform wants regardless of industry. Hard-
# excluded BEFORE the target-company override so e.g. "Branch Banking
# Regional Executive" at Wells Fargo is killed even when Wells is in the
# user's targetCompanies list.
NEVER_RELEVANT_TOKENS = [
    # Bank ops / branches / back-office
    "branch banking", "branch manager", "branch executive", "branch sales",
    "regional banking", "regional banking executive",
    "personal banker", "private banker", "relationship banker",
    "teller", "investment banking analyst", "investment banking associate",
    # Trading floor / markets ops
    "trading platforms support", "trading floor", "trade support",
    "front office trading",
    # KYC / AML / fraud / complaints ops
    "kyc operations", "kyc analyst", "kyc specialist",
    "anti-money laundering", "aml analyst", "aml ops", "aml officer",
    "complaints oversight", "fraud analyst", "fraud specialist",
    "fraud investigator",
    # Lending / credit ops
    "debit operations", "loan officer", "credit analyst", "credit officer",
    "mortgage banker", "mortgage processor", "auto loan officer", "underwriter",
    # Pre-sales / field / customer engineering
    "field cto", "field cio", "field engineer", "solutions engineer",
    "identity specialist", "solutions specialist",
    # Video / content production
    "video strategist", "video producer", "video editor",
    "content moderator", "social media coordinator",
    # IC engineers (engineering LEADERSHIP titles - VP/Head/Director of
    # Engineering - still pass the per-user role gate; only IC titles
    # are blocked here)
    "software engineer", "software developer", "data engineer",
    "backend engineer", "frontend engineer", "full stack engineer",
    "fullstack engineer", "qa engineer", "test engineer",
    "automation engineer", "systems engineer", "platform engineer",
    "infrastructure engineer", "security engineer", "site reliability",
    "devops engineer", "machine learning engineer", "ml engineer",
    "research scientist", "language engineering", "language engineer",
    # FinOps / IT ops noise
    "cloud finops", "finops engineer", "finops analyst",
    # Generic IC ops / claims
    "operations associate", "operations analyst", "operations specialist",
    "operations coordinator", "office coordinator",
    "claims processor", "claims analyst", "claims adjuster",
    # Logistics / warehouse / field service
    "logistics it", "logistics technician", "logistics technical lead",
    "warehouse associate", "warehouse manager",
]

_NEVER_RELEVANT_RE = None

def _build_never_re():
    global _NEVER_RELEVANT_RE
    parts = []
    for tok in NEVER_RELEVANT_TOKENS:
        escaped = re.escape(tok).replace(r"\ ", r"\s+")
        parts.append(r"\b" + escaped + r"\b")
    _NEVER_RELEVANT_RE = re.compile("|".join(parts), re.I)

def _is_never_relevant(title):
    """Universal hard-exclude. Applied before any other gate."""
    global _NEVER_RELEVANT_RE
    if _NEVER_RELEVANT_RE is None: _build_never_re()
    return bool(_NEVER_RELEVANT_RE.search(title or ""))


# Words that appear in any senior title but say nothing about which role
_ROLE_STOPWORDS = {
    "senior", "sr", "junior", "jr", "lead", "leader", "manager", "managers",
    "director", "directors", "head", "chief", "principal", "staff",
    "executive", "vp", "vice", "president", "of", "the", "and", "or", "for",
    "to", "at", "in", "on", "i", "ii", "iii", "iv", "level", "team", "group",
    "global", "us", "north", "america", "leads", "an", "a",
}


def _token_matches(needle, haystack_tokens):
    """A user-token matches a title-token if equal, OR if one is a
    prefix of the other AND the shorter token has >= 4 characters.
    Lets 'health' match 'healthcare' and 'inform' match 'informatics'
    without leaking short tokens like 'it' / 'hr'."""
    if needle in haystack_tokens:
        return True
    if len(needle) < 4:
        return False
    for ht in haystack_tokens:
        if len(ht) < 4:
            continue
        if needle.startswith(ht) or ht.startswith(needle):
            return True
    return False


def _matches_user_role(title, profile):
    """Strict per-user title gate. The title must contain ALL non-stopword
    tokens of at least one of the user's targetTitles (in any order,
    matched via prefix-aware comparison). Falls back to primaryRole.

    Replaces the old global POSITIVE_TITLE_THEMES gate which leaked common
    words ('product', 'strategist', 'ai', 'compliance') to every user
    regardless of their resume. If a real job is being filtered out, the
    user should add the missing targetTitle in the wizard chip editor.
    """
    if not title or not profile:
        return False
    title_l = title.lower()
    title_tokens = set(re.findall(r"[a-z]+", title_l))
    if not title_tokens:
        return False

    for tt in (profile.get("targetTitles") or []):
        tt_l = (tt or "").lower().strip()
        if len(tt_l) < 3:
            continue
        tt_tokens = set(re.findall(r"[a-z]+", tt_l)) - _ROLE_STOPWORDS
        if not tt_tokens:
            continue
        if all(_token_matches(t, title_tokens) for t in tt_tokens):
            return True

    # Fallback to primaryRole tokens + seniority indicator
    primary = (profile.get("primaryRole") or "").lower()
    primary_tokens = set(re.findall(r"[a-z]+", primary)) - _ROLE_STOPWORDS
    if primary_tokens and all(_token_matches(t, title_tokens) for t in primary_tokens):
        seniority_indicators = {
            "vp", "vice", "president", "director", "head", "chief",
            "principal", "staff", "senior", "sr", "lead", "executive",
            "ceo", "coo", "cto", "cio", "ciso", "cpo", "cdo",
        }
        if seniority_indicators & title_tokens:
            return True

    return False


def _has_positive_theme(title, profile):
    """Title qualifies if it contains a positive domain theme OR any of the
    AI-extracted profile signals (keywords, specialties, targetTitles, regulations)."""
    global _POSITIVE_THEME_RE
    if _POSITIVE_THEME_RE is None:
        _build_positive_re()
    t = title or ""
    if _POSITIVE_THEME_RE.search(t):
        return True
    if profile:
        t_lower = t.lower()
        # Check across multiple richer profile fields
        for field in ("keywords", "specialties", "targetTitles", "regulations", "frameworks", "technologies"):
            for term in profile.get(field, []) or []:
                if not term:
                    continue
                term_l = term.lower()
                # Multi-word terms use substring match; single words use word boundaries
                if " " in term_l or "-" in term_l:
                    if term_l in t_lower:
                        return True
                else:
                    if re.search(r"\b" + re.escape(term_l) + r"\b", t_lower):
                        return True
    return False


# ============================================================
# F3: Seniority rank — maps a job title and a user's seniorityLevel
# to a 0..5 rank. Higher = more senior. Used to filter out jobs below
# the user's level.
# ============================================================
def _job_seniority_rank(title):
    t = (title or "").lower()
    if re.search(r"\b(ceo|cto|cio|coo|ciso|cpo|cdo|cfo|chief|founder|co-founder)\b", t):
        return 5
    if re.search(r"\b(svp|evp|senior vice president|executive vice president|vp|vice president)\b", t):
        return 4
    if re.search(r"\b(director|head of|managing director|general manager|gm)\b", t):
        return 3
    if re.search(r"\b(principal|staff|senior|sr|lead|architect)\b", t):
        return 2
    if re.search(r"\b(manager)\b", t):
        return 1
    return 0


def _user_min_seniority_rank(profile):
    if not profile:
        return 0
    sl = (profile.get("seniorityLevel") or "").lower()
    pr = (profile.get("primaryRole") or "").lower()
    blob = sl + " " + pr
    if not blob.strip():
        return 0
    # Use word-boundary regex (not substring) so "director" doesn't match "cto"
    def _has(*terms):
        for t in terms:
            if re.search(r"\b" + re.escape(t) + r"\b", blob):
                return True
        return False
    if _has("ceo", "cto", "cio", "coo", "ciso", "cpo", "cdo", "cfo", "chief", "founder"):
        return 4   # one level below their listed (Chief) - show VPs too
    if _has("vp", "vice president", "svp", "evp"):
        return 3   # VPs see Director+ ; cuts the Manager/Senior IC noise
    if _has("director", "head of", "principal", "managing director"):
        return 2   # Directors see Senior+ titles
    if _has("senior", "sr", "staff", "lead"):
        return 1   # Seniors see Manager+
    return 0


# ============================================================
# F4: Salary filter helpers
# ============================================================
def _passes_salary_filter(salary_str, salary_max_parsed, profile):
    """Return True if this row should pass the salary gate based on user prefs.
    profile.salaryFloor (number) — hide jobs below this
    profile.hideNoSalary (bool)  — hide jobs whose salary_range is empty
    Empty strings/None disable the filter.
    """
    if not profile:
        return True
    hide_no_sal = bool(profile.get("hideNoSalary"))
    floor = profile.get("salaryFloor")
    try:
        floor_n = int(float(floor)) if floor else 0
    except (TypeError, ValueError):
        floor_n = 0
    has_salary = bool((salary_str or "").strip())
    if hide_no_sal and not has_salary:
        return False
    if floor_n and has_salary and salary_max_parsed and salary_max_parsed < floor_n:
        return False
    return True


# ============================================================
# F1: Negative-title filter (server side mirror of user dismissals)
# ============================================================
def _matches_negative_title(title, profile):
    """Return True if the title matches any of the user's negativeTitles
    (subset-of-tokens match, prefix-aware, same as _matches_user_role)."""
    if not title or not profile:
        return False
    neg = profile.get("negativeTitles") or []
    if not neg:
        return False
    title_l = title.lower()
    title_tokens = set(re.findall(r"[a-z]+", title_l))
    if not title_tokens:
        return False
    for nt in neg:
        nt_l = (nt or "").lower().strip()
        if len(nt_l) < 3:
            continue
        nt_tokens = set(re.findall(r"[a-z]+", nt_l)) - _ROLE_STOPWORDS
        if not nt_tokens:
            continue
        if all(_token_matches(t, title_tokens) for t in nt_tokens):
            return True
    return False


def _normalize_title(title):
    """Lowercase, strip stop words, then concatenate alphanumerics so minor wording
    differences ('Director of Product' vs 'Director, Product') collapse to the same hash."""
    words = re.split(r"[^a-z0-9]+", (title or "").lower())
    return "".join(w for w in words if w and w not in STOP_WORDS)


def fingerprint(job):
    """Stable hash so the same role across reposts/sources dedupes."""
    base = f"{job['company_slug']}|{_normalize_title(job['title'])}|{re.sub(r'[^a-z0-9]+', '', (job['location'] or '').lower())}"
    return sha256(base.encode()).hexdigest()[:16]


def is_remote(job):
    blob = f"{job['location']} {job['title']} {job['description'][:500]}".lower()
    if "remote" in blob or "anywhere" in blob or "work from home" in blob:
        return True
    if "hybrid" in blob and "remote" in blob:
        return True
    return False


def is_senior(job):
    t = (job["title"] or "").lower()
    return any(term in t for term in SENIOR_TITLE_TERMS)


# --- Skills profile (loaded per-user, used for scoring) ------------------
WORKER_BASE_URL = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev"
USERS_JSON_PATH = os.path.join(ROOT, "users.json")
SKILLS_PROFILE = None  # set per user during generate_dashboard
COMPANY_INDUSTRIES = {}  # company_slug -> list of industries (populated from companies.json)
DEFAULT_INDUSTRIES = ["healthcare", "digital-health"]


# --- Industry matching --------------------------------------------------
_INDUSTRY_STOPWORDS = {"and", "the", "for", "with", "of", "to", "in", "on",
                       "management", "services", "company", "industry",
                       # Weak cross-industry tokens — too generic to indicate
                       # real overlap. Without these, "consumer-banking" matched
                       # "direct-to-consumer", leaking Capital One PM jobs onto a
                       # healthcare-IT dashboard.
                       "consumer", "data", "digital", "technology", "tech",
                       "enterprise", "saas", "cloud", "global", "platform",
                       "solutions", "systems", "software", "ai", "ml",
                       "innovation", "products", "product", "strategy",
                       "operations", "service", "international", "north",
                       "america", "americas", "online", "mobile", "web",
                       "info", "information"}


def _industry_tokens(industries):
    """Return a set of lowercase normalized tokens from a list of industry strings."""
    tokens = set()
    for s in industries or []:
        # Normalize: lowercase, replace separators with space
        norm = re.sub(r"[^a-z0-9]+", " ", str(s).lower())
        for word in norm.split():
            if len(word) > 2 and word not in _INDUSTRY_STOPWORDS:
                tokens.add(word)
    return tokens


def _industry_match(company_industries, user_industries):
    """Returns True if the company's industries overlap with the user's profile industries."""
    if not user_industries:
        return True  # No profile → show all
    if not company_industries:
        return False  # Untagged company → hide
    ct = _industry_tokens(company_industries)
    ut = _industry_tokens(user_industries)
    return bool(ct & ut)


def load_skills_profile(slug="geetu"):
    """Fetch the AI-generated skills profile for a specific user from the Worker.
    Returns None on failure — scoring falls back to legacy hardcoded keywords."""
    try:
        url = WORKER_BASE_URL + "/skills-profile?user=" + slug
        req = Request(url, headers={"User-Agent": "fetch_jobs.py"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        profile = data.get("profile")
        if not profile or not isinstance(profile, dict):
            return None
        for k in ("keywords", "seniorityTitles", "industries", "negativeKeywords"):
            if isinstance(profile.get(k), list):
                profile[k] = [str(x).lower().strip() for x in profile[k] if x]
            else:
                profile[k] = []
        return profile
    except Exception as e:
        print(f"[skills-profile:{slug}] could not load: {e}", flush=True)
        return None


def load_users():
    """Fetch user list from Worker /users endpoint. Falls back to users.json on failure,
    then to a hardcoded default. The Worker is the canonical registry."""
    # Primary: Worker /users
    try:
        req = Request(WORKER_BASE_URL + "/users", headers={"User-Agent": "fetch_jobs.py"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        users = data.get("users", [])
        if isinstance(users, list) and users:
            print(f"[users] loaded {len(users)} from Worker", flush=True)
            return users
    except Exception as e:
        print(f"[users] Worker fetch failed ({e}), falling back to users.json", flush=True)

    # Fallback: users.json (legacy)
    try:
        with open(USERS_JSON_PATH) as f:
            users = json.load(f)
        if isinstance(users, list) and users:
            return users
    except Exception:
        pass

    # Last resort
    print("[users] using hardcoded default (geetu)", flush=True)
    return [{"slug": "geetu", "name": "Geetanjali Arora"}]


def score_job(job):
    """0-100 score. Higher = more relevant + more likely 'real'.
    Uses the AI-extracted skills profile when available; falls back to hardcoded keywords."""
    s = 50
    blob = f"{job['title']} {job['description']}".lower()
    title = (job["title"] or "").lower()

    # Profile mismatch — bring to very low score so it won't appear
    if _is_irrelevant_title(job["title"]):
        return 0

    profile = SKILLS_PROFILE
    if profile:
        # AI-driven negative keywords — disqualify on title match
        neg = profile.get("negativeKeywords", [])
        if any(n and n in title for n in neg):
            return 0

        # Seniority match from profile
        sen_titles = profile.get("seniorityTitles", []) or SENIOR_TITLE_TERMS
        if any(t in title for t in sen_titles):
            s += 15

        # Profile-driven keyword relevance — weighted hits
        kw_hits = sum(1 for k in profile.get("keywords", []) if k and k in blob)
        s += min(kw_hits * 3, 25)

        # Industry match — title or company hint
        ind_hits = sum(1 for i in profile.get("industries", []) if i and i in blob)
        s += min(ind_hits * 2, 8)
    else:
        # Legacy path — used when Worker is unreachable
        if is_senior(job):
            s += 15
        hits = sum(1 for t in RELEVANCE_TERMS if t in blob)
        s += min(hits * 2, 20)

    # Remote bonus
    if is_remote(job):
        s += 10

    # Red flags
    if any(t in blob for t in SCAM_TERMS):
        s -= 40
    if any(t in blob for t in AGENCY_TERMS):
        s -= 20

    # Empty / very short description = suspicious
    if len(job["description"]) < 200:
        s -= 10

    return max(0, min(100, s))


# --- Storage -------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    fingerprint TEXT PRIMARY KEY,
    source TEXT,
    company_slug TEXT,
    company_name TEXT,
    external_id TEXT,
    title TEXT,
    location TEXT,
    url TEXT,
    posted_at TEXT,
    description TEXT,
    first_seen TEXT,
    last_seen TEXT,
    sightings INTEGER DEFAULT 1,
    remote INTEGER,
    senior INTEGER,
    score INTEGER,
    salary_range TEXT
);
CREATE INDEX IF NOT EXISTS idx_score ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_last_seen ON jobs(last_seen DESC);
"""


def get_conn():
    # Self-heal: if the DB file exists but is corrupt/empty, wipe it and retry.
    for attempt in range(2):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(SCHEMA)
            # Migration: add salary_range to older DBs that don't have it
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN salary_range TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists
            # Migration: add employment_type column
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN employment_type TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            # Migration: add industries column (comma-separated)
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN industries TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            return conn
        except sqlite3.DatabaseError:
            if attempt == 0 and os.path.exists(DB_PATH):
                try:
                    os.remove(DB_PATH)
                    for sidecar in (DB_PATH + "-journal", DB_PATH + "-wal", DB_PATH + "-shm"):
                        if os.path.exists(sidecar):
                            os.remove(sidecar)
                except OSError:
                    pass
            else:
                raise


def upsert_job(conn, job):
    fp = fingerprint(job)
    now = datetime.now(timezone.utc).isoformat()
    remote = 1 if is_remote(job) else 0
    senior = 1 if is_senior(job) else 0
    score = score_job(job)

    salary = job.get("salary_range") or ""
    employment_type = detect_employment_type(job)
    # Industries: looked up from COMPANY_INDUSTRIES based on company_slug (lowercased)
    industries = COMPANY_INDUSTRIES.get((job.get("company_slug") or "").lower(), DEFAULT_INDUSTRIES)
    industries_str = ",".join(industries) if industries else ""
    cur = conn.execute("SELECT fingerprint, sightings FROM jobs WHERE fingerprint=?", (fp,))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE jobs SET last_seen=?, sightings=sightings+1, score=?, remote=?, senior=?, salary_range=?, employment_type=?, industries=? WHERE fingerprint=?",
            (now, score, remote, senior, salary, employment_type, industries_str, fp),
        )
    else:
        conn.execute(
            """INSERT INTO jobs (fingerprint, source, company_slug, company_name, external_id,
               title, location, url, posted_at, description, first_seen, last_seen,
               sightings, remote, senior, score, salary_range, employment_type, industries)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)""",
            (fp, job["source"], job["company_slug"], job["company_name"], job["external_id"],
             job["title"], job["location"], job["url"], job["posted_at"], job["description"],
             now, now, remote, senior, score, salary, employment_type, industries_str),
        )


# --- Main pipeline -------------------------------------------------------

def _build_company_industries(companies):
    """Populate COMPANY_INDUSTRIES from companies.json.
    Each entry can be a slug string (uses _default_industries) or {slug, industries}."""
    global COMPANY_INDUSTRIES, DEFAULT_INDUSTRIES
    defaults = companies.get("_default_industries")
    if defaults:
        DEFAULT_INDUSTRIES = defaults
    mapping = {}
    for source in ("greenhouse", "lever", "ashby"):
        for entry in companies.get(source, []):
            if isinstance(entry, str):
                mapping[entry.lower()] = DEFAULT_INDUSTRIES
            elif isinstance(entry, dict) and entry.get("slug"):
                mapping[entry["slug"].lower()] = entry.get("industries", DEFAULT_INDUSTRIES)
    for entry in companies.get("workday", []):
        if isinstance(entry, dict):
            key = (entry.get("tenant") or entry.get("name", "")).lower()
            if key:
                mapping[key] = entry.get("industries", DEFAULT_INDUSTRIES)
    for entry in companies.get("wttj", []):
        if isinstance(entry, dict):
            key = (entry.get("slug") or entry.get("name", "")).lower()
            if key:
                mapping[key] = entry.get("industries", DEFAULT_INDUSTRIES)
    COMPANY_INDUSTRIES = mapping
    print(f"[industries] mapped {len(mapping)} companies; default={DEFAULT_INDUSTRIES}", flush=True)


def _slugify_company_name(name):
    """Lowercase, drop non-alphanumerics — best-effort guess at the ATS slug from a company name."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def _merge_user_target_companies(companies):
    """Path 2: read each user's profile.targetCompanies (AI-suggested) and merge them
    into the in-memory companies dict so the scraper picks them up. No-op if no user
    profile has targetCompanies yet (e.g. before the Worker prompt is updated)."""
    try:
        users = load_users()
    except Exception as e:
        print(f"[user-targets] load_users failed: {e}", flush=True)
        return

    # Track what slugs/tenants already exist per ATS so we don't duplicate
    existing = {ats: set() for ats in ("greenhouse", "lever", "ashby")}
    existing["workday"] = set()
    for ats in ("greenhouse", "lever", "ashby"):
        for entry in companies.get(ats, []):
            if isinstance(entry, str):
                existing[ats].add(entry.lower())
            elif isinstance(entry, dict) and entry.get("slug"):
                existing[ats].add(entry["slug"].lower())
    for entry in companies.get("workday", []):
        if isinstance(entry, dict) and entry.get("tenant"):
            existing["workday"].add(entry["tenant"].lower())

    added = {ats: 0 for ats in ("greenhouse", "lever", "ashby")}
    skipped = 0

    for u in users:
        slug = (u.get("slug") if isinstance(u, dict) else u) or ""
        if not slug:
            continue
        try:
            profile = load_skills_profile(slug) or {}
        except Exception as e:
            print(f"[user-targets:{slug}] profile fetch failed: {e}", flush=True)
            continue

        targets = profile.get("targetCompanies") or []
        if not targets:
            continue

        user_industries = profile.get("industries", []) or []

        for t in targets:
            # Each target can be a dict {name, atsHint, why} or a bare string name
            if isinstance(t, str):
                name = t
                hint = "greenhouse"
            elif isinstance(t, dict):
                name = t.get("name") or t.get("slug") or ""
                hint = (t.get("atsHint") or t.get("ats") or "greenhouse").lower()
            else:
                continue
            if not name:
                continue

            target_slug = _slugify_company_name(t.get("slug") if isinstance(t, dict) and t.get("slug") else name)

            # Greenhouse/Lever/Ashby take a simple slug; Workday needs tenant+subdomain+site
            # which we now try to parse from an atsUrl the AI may have provided.
            if hint == "workday":
                ats_url = t.get("atsUrl") if isinstance(t, dict) else None
                wd_tenant = wd_subdomain = wd_site = None
                if ats_url:
                    # Parse https://{tenant}.{subdomain}.myworkdayjobs.com/{site}
                    wd_match = re.match(
                        r"https?://([^./]+)\.(wd\d+)\.myworkdayjobs\.com/([^/?#]+)",
                        ats_url,
                    )
                    if wd_match:
                        wd_tenant, wd_subdomain, wd_site = wd_match.groups()
                if not wd_tenant:
                    # Slice 3.5 fallback heuristic: AI didn't give us a usable atsUrl,
                    # but workday tenant slugs often follow a predictable pattern. Try
                    # the most common combo (wd1 + Careers/External) so the scraper
                    # gets a chance — it will fail gracefully if the slug is wrong.
                    wd_tenant = target_slug
                    wd_subdomain = "wd1"
                    wd_site = "Careers"
                    print(f"[user-targets:{slug}] workday fallback for '{name}' -> {wd_tenant}.{wd_subdomain}.myworkdayjobs.com/{wd_site} (no atsUrl from AI)", flush=True)
                wd_key = wd_tenant.lower()
                if wd_key in existing.setdefault("workday", set()):
                    continue
                companies.setdefault("workday", []).append({
                    "name": name,
                    "tenant": wd_tenant,
                    "subdomain": wd_subdomain,
                    "site": wd_site,
                    "industries": user_industries or DEFAULT_INDUSTRIES,
                    "_added_by_user": slug,
                })
                existing["workday"].add(wd_key)
                added.setdefault("workday", 0)
                added["workday"] += 1
                continue

            if hint == "wttj":
                wttj_key = target_slug
                existing.setdefault("wttj", set())
                if wttj_key in existing["wttj"]:
                    continue
                companies.setdefault("wttj", []).append({
                    "slug": wttj_key,
                    "name": name,
                    "industries": user_industries or DEFAULT_INDUSTRIES,
                    "_added_by_user": slug,
                })
                existing["wttj"].add(wttj_key)
                added.setdefault("wttj", 0)
                added["wttj"] += 1
                continue
            if hint not in ("greenhouse", "lever", "ashby"):
                skipped += 1
                continue
            if target_slug in existing[hint]:
                continue

            companies.setdefault(hint, []).append({
                "slug": target_slug,
                "industries": user_industries or DEFAULT_INDUSTRIES,
                "_added_by_user": slug,  # debugging breadcrumb
            })
            existing[hint].add(target_slug)
            added[hint] += 1

    total = sum(added.values())
    if total:
        print(f"[user-targets] merged {total} per-user companies (greenhouse={added['greenhouse']}, lever={added['lever']}, ashby={added['ashby']}); skipped {skipped} non-routable", flush=True)
    else:
        print(f"[user-targets] no targetCompanies in any user profile yet (Worker prompt may not be updated)", flush=True)


def run():
    with open(COMPANIES_PATH) as f:
        companies = json.load(f)

    _build_company_industries(companies)

    # Path 2: merge per-user target companies (AI-suggested) into the scrape list,
    # then refresh the industry mapping to include them. No-op if no user profile
    # has targetCompanies yet (i.e. before the Worker /parse-resume prompt update).
    _merge_user_target_companies(companies)
    _build_company_industries(companies)

    conn = get_conn()
    totals = {"greenhouse": 0, "lever": 0, "ashby": 0}
    failures = []

    totals["workday"] = 0
    for source, fetcher in SOURCES.items():
        entries = companies.get(source, [])
        print(f"\n[{source}] {len(entries)} companies")
        for i, entry in enumerate(entries, 1):
            # Backward compat: entry may be a slug string OR an object {slug, industries}
            if isinstance(entry, dict) and entry.get("slug"):
                fetch_arg = entry["slug"]
            elif isinstance(entry, dict):
                fetch_arg = entry  # workday-style
            else:
                fetch_arg = entry
            label = entry.get("name", entry.get("tenant", "?")) if isinstance(entry, dict) else entry
            try:
                jobs = fetcher(fetch_arg)
                if not jobs:
                    failures.append(f"{source}:{label}")
                    print(f"  [{i}/{len(entries)}] {label}: 0 jobs (slug may be invalid)")
                    continue
                for j in jobs:
                    upsert_job(conn, j)
                totals[source] = totals.get(source, 0) + len(jobs)
                print(f"  [{i}/{len(entries)}] {label}: {len(jobs)} jobs")
            except Exception as e:
                failures.append(f"{source}:{label} ({e})")
                print(f"  [{i}/{len(entries)}] {label}: ERROR — {e}")
            time.sleep(0.15)  # be polite

        conn.commit()

    print(f"\nTotals: {totals}")
    print(f"Failures: {len(failures)} (companies returned no data — likely bad slugs)")

    # Note: scoring used the LAST loaded skills profile during fetch. The dashboard
    # generation step re-loads each user's profile before filtering for that user,
    # so per-user views are correct even if scoring is global.
    generate_all_dashboards(conn)
    conn.close()


def _parse_salary_max(salary_text):
    """Return the highest dollar value appearing in the salary string (in whole dollars), or 0."""
    if not salary_text:
        return 0
    best = 0
    for m in re.finditer(r"\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}\s?k|\d{4,7})", salary_text, flags=re.IGNORECASE):
        raw = m.group(1).replace(",", "").replace(" ", "")
        try:
            if raw.lower().endswith("k"):
                val = int(float(raw[:-1]) * 1000)
            else:
                val = int(raw)
            if val > best:
                best = val
        except Exception:
            continue
    return best


def _location_remote_ok(r, user_locations, remote_pref):
    """Filter for user's location + remote preference.
    r[3] = loc (string), r[9] = remote (0|1).
    remote_pref: "remote-only" | "hybrid" | "onsite" | "any" | None"""
    job_loc = (r[3] or "").lower()
    is_remote_job = bool(r[9])
    pref = (remote_pref or "any").lower().strip()

    # Remote-only users: drop non-remote jobs
    if pref == "remote-only" and not is_remote_job:
        return False

    # Onsite-only users: drop fully-remote jobs (allow hybrid via location match)
    if pref == "onsite" and is_remote_job and not any(
        (loc or "").lower() in job_loc for loc in (user_locations or [])
    ):
        return False

    # If user listed specific locations, the job must either be remote OR match one of them
    if user_locations:
        normalized = [(loc or "").lower().strip() for loc in user_locations if loc]
        # "remote (us)" type entries effectively whitelist remote jobs
        wants_remote = any("remote" in loc for loc in normalized)
        location_match = any(loc and loc in job_loc for loc in normalized if "remote" not in loc)
        if not (is_remote_job and wants_remote) and not location_match:
            # Be permissive when remotePreference is "any" or "hybrid"
            if pref in ("remote-only", "onsite"):
                return False
            # For hybrid/any with no location match, still return True (soft filter elsewhere)
    return True


def generate_dashboard(conn, user_slug="geetu", user_name="Geetanjali Arora", output_path=None):
    """Generate the dashboard HTML for a specific user.
    output_path defaults to <user_slug>.html (or index.html for backward compat if slug='geetu')."""
    global SKILLS_PROFILE
    # Load this user's skills profile from the Worker (sets the global used by score_job)
    SKILLS_PROFILE = load_skills_profile(user_slug)
    if SKILLS_PROFILE:
        print(f"[skills-profile:{user_slug}] {SKILLS_PROFILE.get('primaryRole','?')} "
              f"· {len(SKILLS_PROFILE.get('keywords', []))} keywords", flush=True)
    else:
        print(f"[skills-profile:{user_slug}] not available — using fallback themes only", flush=True)

    if output_path is None:
        output_path = os.path.join(ROOT, f"{user_slug}.html")

    rows = conn.execute("""
        SELECT fingerprint, company_name, title, location, url, posted_at, first_seen, last_seen,
               sightings, remote, senior, score, description, salary_range, employment_type, industries
        FROM jobs
        WHERE last_seen >= datetime('now', '-30 days')
        ORDER BY score DESC, last_seen DESC
        LIMIT 20000
    """).fetchall()
    # No profile → no jobs. User must upload resume first to see anything.
    if not SKILLS_PROFILE:
        rows = []
    # Hide jobs that aren't a fit (blacklist)
    rows = [r for r in rows if not _is_irrelevant_title(r[2])]

    # Combine the title-keyword whitelist, the industry filter, and a
    # target-company override into a single pass (Slice B v2). The previous
    # behavior required BOTH title-pass AND industry-pass, which over-filtered
    # senior roles at verified target companies whose titles didn't happen to
    # contain a healthcare-flavored theme word. New semantics:
    #
    #   pass IF (title matches user themes/keywords AND industry overlaps)
    #     OR (job is senior=1 AND its company is in user's targetCompanies)
    #
    # When the user has no industries set, the industry check is treated as
    # always-pass so the title gate alone applies.
    if SKILLS_PROFILE:
        user_industries = (SKILLS_PROFILE.get("industries", []) or []) + (SKILLS_PROFILE.get("specialties", []) or [])
        target_company_names = {
            (tc.get("name") if isinstance(tc, dict) else tc or "").strip().lower()
            for tc in (SKILLS_PROFILE.get("targetCompanies") or [])
            if (tc.get("name") if isinstance(tc, dict) else tc)
        }
        # Company-size preference (Slice B v3). Prefer the new companySizeMix
        # (object with %s for each size) — hard-exclude any size at 0%. Fall
        # back to the older companySizePreferences (array of picked sizes) so
        # we don't break profiles that haven't been re-saved yet.
        size_mix = SKILLS_PROFILE.get("companySizeMix") or {}
        if isinstance(size_mix, dict) and size_mix:
            size_prefs = {k.lower() for k, v in size_mix.items() if isinstance(v, (int, float)) and v > 0}
            if not size_prefs:
                size_prefs = {"startup", "midsize", "large"}
        else:
            prefs = SKILLS_PROFILE.get("companySizePreferences") or []
            size_prefs = {p.lower() for p in prefs if isinstance(p, str)} or {"startup", "midsize", "large"}
    else:
        user_industries = []
        target_company_names = set()
        size_prefs = {"startup", "midsize", "large"}

    # Load size lookup. Build a single map keyed by lowercased company_name and
    # by lowercased slug/tenant for fallback. Built once per dashboard.
    try:
        with open(COMPANIES_PATH) as _cf:
            _cdoc = json.load(_cf)
        _raw_sizes = _cdoc.get("_company_sizes") or {}
        _size_by_company = {}
        # 1. Workday entries: key by name (lowercase)
        for _e in _cdoc.get("workday", []):
            if isinstance(_e, dict) and _e.get("name") and _e["name"] in _raw_sizes:
                _size_by_company[_e["name"].lower()] = _raw_sizes[_e["name"]]
        # 2. Greenhouse/Lever/Ashby: slug -> tagged size. The DB stores
        #    company_name which may differ from slug, so we also keep the
        #    slug map and resolve at query time via _company_slug if needed.
        # For safety we store both name-lower and the slug itself.
        _slug_to_size = {k.lower(): v for k, v in _raw_sizes.items()}
        # 3. Staffing / recruiting firms — used for the "Recruiters: hide/show/only"
        #    dashboard toggle. Lowercased for case-insensitive match.
        _recruiter_names = {(s or "").strip().lower() for s in (_cdoc.get("_recruiting_firms") or [])}
    except Exception:
        _size_by_company = {}
        _slug_to_size = {}
        _recruiter_names = set()

    def _company_size(company_name, company_slug=""):
        """Best-effort lookup of size bucket for a job's company."""
        if not company_name:
            return None
        nm = company_name.strip().lower()
        if nm in _size_by_company:
            return _size_by_company[nm]
        if nm in _slug_to_size:
            return _slug_to_size[nm]
        slug = (company_slug or "").strip().lower()
        if slug and slug in _slug_to_size:
            return _slug_to_size[slug]
        return None


    def _passes_filters(r):
        title = r[2]
        company = (r[1] or "").strip().lower()
        senior_flag = r[10]
        salary_str = r[13]
        job_inds = (r[15] or "").split(",") if r[15] else []

        # Universal hard-exclude: bank back-office, IC engineers, pre-sales
        # field roles, content production. Applied BEFORE the target-company
        # override so e.g. "Branch Banking Regional Executive" at Wells Fargo
        # is killed even when Wells is in the user's targetCompanies list.
        if _is_never_relevant(title):
            return False

        # F1: user dismissed similar titles before — hide.
        if SKILLS_PROFILE and _matches_negative_title(title, SKILLS_PROFILE):
            return False

        # F3: seniority floor — hide jobs below the user's listed seniority.
        if SKILLS_PROFILE:
            min_rank = _user_min_seniority_rank(SKILLS_PROFILE)
            if min_rank > 0 and _job_seniority_rank(title) < min_rank:
                return False

        # F4: salary floor + must-list-pay (only when user opted in).
        if SKILLS_PROFILE:
            smax = _parse_salary_max(salary_str)
            if not _passes_salary_filter(salary_str, smax, SKILLS_PROFILE):
                return False

        # Hard-filter by company-size preference when the user has selected
        # only some sizes. If size is unknown (untagged company), let it
        # through so we don't accidentally hide everything.
        if len(size_prefs) < 3:
            sz = _company_size(company)
            if sz is not None and sz not in size_prefs:
                return False

        # Strict per-user title gate. The title must match one of the
        # user's own targetTitles (or primaryRole). Replaces the old global
        # theme list which leaked words like "product" / "strategist" /
        # "ai" / "compliance" to every user regardless of their resume.
        if SKILLS_PROFILE:
            if not _matches_user_role(title, SKILLS_PROFILE):
                return False
        else:
            # No profile loaded (extremely rare - awaiting upload). Fall
            # back to legacy broad-theme gate so the dashboard is not
            # completely empty.
            if not _has_positive_theme(title, None):
                return False

        # Target-company override: user explicitly named this employer, so
        # waive the industry-overlap check below. The title gate above
        # still had to pass.
        if senior_flag and company and company in target_company_names:
            return True

        if user_industries and job_inds:
            return _industry_match(job_inds, user_industries)
        return True  # no industry data on either side — title gate is enough

    rows = [r for r in rows if _passes_filters(r)]

    # Multi-location dedup: many enterprise employers (CVS, BMO, BofA) post
    # the same role in hundreds of stores/branches — separate fingerprints
    # because location is in the hash, but logically the same job. Collapse
    # to one card per (company, normalized title); record location count.
    _dedup = {}
    _location_counts = {}
    _order = []
    for r in rows:
        company_key = (r[1] or "").strip().lower()
        title_key = _normalize_title(r[2] or "")
        key = (company_key, title_key)
        if key in _dedup:
            _location_counts[key] += 1
            # Keep the row with the highest score
            if r[11] is not None and r[11] > (_dedup[key][11] or 0):
                _dedup[key] = r
        else:
            _dedup[key] = r
            _location_counts[key] = 1
            _order.append(key)
    rows = [_dedup[k] for k in _order]
    # Stash per-row location count so card rendering can show a "Nx locations" badge
    LOCATION_COUNTS = {(_dedup[k][0]): _location_counts[k] for k in _order}

    # Location + remote preference filter (Slice 2)
    if SKILLS_PROFILE:
        user_locations = SKILLS_PROFILE.get("preferredLocations", []) or []
        remote_pref = SKILLS_PROFILE.get("remotePreference") or (
            "remote-only" if SKILLS_PROFILE.get("remotePreferred") else "any"
        )
    else:
        user_locations = []
        remote_pref = "any"
    if user_locations or remote_pref not in ("any", None, ""):
        before_loc = len(rows)
        rows = [r for r in rows if _location_remote_ok(r, user_locations, remote_pref)]
        print(f"[location-remote:{user_slug}] filter pref={remote_pref!r} locs={user_locations[:3]} kept {len(rows)}/{before_loc}", flush=True)

    # Hide ghost jobs (listed > GHOST_DAYS) from default view
    def _not_ghost(r):
        posted_at, first_seen = r[5], r[6]
        ld = _days_old(posted_at) if posted_at else (_days_old(first_seen) if first_seen else 0)
        return ld is None or ld <= GHOST_DAYS
    rows = [r for r in rows if _not_ghost(r)]

    rows = rows[:1000]

    # Stats
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    senior_remote = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE senior=1 AND remote=1 AND last_seen >= datetime('now','-7 days')"
    ).fetchone()[0]
    ghost = conn.execute(
        f"SELECT COUNT(*) FROM jobs WHERE julianday(last_seen) - julianday(first_seen) > {GHOST_DAYS}"
    ).fetchone()[0]

    # F5: cross-company cluster — group by normalized title and stash a
    # list of *other* companies sharing the same title so the card can
    # render an "Also at X, Y, Z" badge.
    _xc_by_norm = {}
    for r in rows:
        key = _normalize_title(r[2] or "")
        if not key: continue
        cname = (r[1] or "").strip()
        if not cname: continue
        _xc_by_norm.setdefault(key, []).append(cname)
    # Dedup company names per key (preserve first-seen order)
    for k, lst in list(_xc_by_norm.items()):
        seen = set(); uniq = []
        for c in lst:
            cl = c.lower()
            if cl in seen: continue
            seen.add(cl); uniq.append(c)
        _xc_by_norm[k] = uniq

    # F5: pre-compute "why matched" per row.
    def _why_matched(r):
        if not SKILLS_PROFILE: return ""
        title = r[2] or ""; company = (r[1] or "").strip()
        title_tokens = set(re.findall(r"[a-z]+", title.lower()))
        reasons = []
        for tt in (SKILLS_PROFILE.get("targetTitles") or []):
            tt_tokens = set(re.findall(r"[a-z]+", (tt or "").lower())) - _ROLE_STOPWORDS
            if tt_tokens and all(_token_matches(t, title_tokens) for t in tt_tokens):
                reasons.append(f"matches your target title “{tt}”")
                break
        if not reasons:
            primary = (SKILLS_PROFILE.get("primaryRole") or "")
            if primary:
                reasons.append(f"matches your role “{primary}”")
        tcompanies = {c.get("name","").lower() for c in (SKILLS_PROFILE.get("targetCompanies") or [])}
        if company and company.lower() in tcompanies:
            reasons.append(f"{company} is on your target-companies list")
        job_inds = (r[15] or "").split(",") if r[15] else []
        ind_overlap = list(_industry_tokens(job_inds) & _industry_tokens(SKILLS_PROFILE.get("industries") or []))
        if ind_overlap:
            reasons.append("industry overlap: " + ", ".join(ind_overlap[:3]))
        return " • ".join(reasons) if reasons else "passed default gates"

    cards = []
    for r in rows:
        (fp, company, title, loc, url, posted_at, first_seen, last_seen,
         sightings, remote, senior, score, desc, salary, employment_type, _industries) = r
        emp = (employment_type or "unknown").lower()
        # "Listed" age — prefer the source's posted_at, fall back to first_seen
        listed_days = _days_old(posted_at) if posted_at else None
        if listed_days is None:
            listed_days = _days_old(first_seen) or 0
        ghost_flag = listed_days is not None and listed_days > GHOST_DAYS
        salary = (salary or "").strip()
        salary_max = _parse_salary_max(salary)
        badges = []
        if senior: badges.append('<span class="b senior">Senior</span>')
        if remote: badges.append('<span class="b remote">Remote</span>')
        if emp == "contract": badges.append('<span class="b contract">Contract</span>')
        if listed_days == 0: badges.append('<span class="b fresh">New today</span>')
        elif listed_days is not None and listed_days <= 7: badges.append('<span class="b week">This week</span>')
        _loc_count = LOCATION_COUNTS.get(fp, 1)
        if _loc_count > 1: badges.append(f'<span class="b multi-loc">{_loc_count} locations</span>')
        if ghost_flag: badges.append(f'<span class="b ghost">Ghost? {listed_days}d</span>')
        if sightings > 3: badges.append(f'<span class="b repost">Seen {sightings}×</span>')
        badge_html = " ".join(badges)
        salary_html = f'<div class="salary-row"><span class="salary">{_esc(salary)}</span></div>' if salary else ''

        _is_recr = 1 if (company or "").strip().lower() in _recruiter_names else 0
        _why = _why_matched(r)
        _norm_key = _normalize_title(title or "")
        _xc_others = [c for c in _xc_by_norm.get(_norm_key, []) if c.lower() != (company or "").lower()]
        _xc_count = len(_xc_others)
        _xc_label = ", ".join(_xc_others[:4]) + (f" +{_xc_count - 4} more" if _xc_count > 4 else "")
        cards.append(f"""
        <div class="card" data-fp="{fp}" data-score="{score}" data-senior="{senior}" data-remote="{remote}" data-employment="{emp}" data-listed-days="{listed_days if listed_days is not None else 9999}" data-salary-max="{salary_max}" data-last-seen="{last_seen or ''}" data-first-seen="{first_seen or ''}" data-recruiter="{_is_recr}" data-why="{_esc(_why)}" data-cluster-count="{_xc_count}" data-cluster-companies="{_esc(_xc_label)}" data-title-norm="{_norm_key}">
          <div class="row1">
            <div class="title"><a href="{url}" target="_blank">{_esc(title)}</a></div>
            <div class="score">{score}</div>
          </div>
          <div class="row2">
            <span class="company">{_esc(company)}</span> ·
            <span class="loc">{_esc(loc or 'Location N/A')}</span> ·
            <span class="age">{listed_days}d old</span>
          </div>
          {salary_html}
          <div class="badges" data-badges>{badge_html}</div>
          <div class="desc">{_esc(_strip_html(desc)[:300])}…</div>
          <div class="actions">
            <button class="btn primary" onclick="applyAndOpen('{fp}', this, '{url}')">Apply now &rarr;</button>
            <button class="btn ghost-btn" onclick="prepApplication('{fp}', this)">Prep materials</button>
            <button class="btn track" onclick="cycleStatus('{fp}', this)" data-status-for="{fp}">Mark Applied</button>
            <button class="btn ghost-btn small" onclick="showWhyMatched('{fp}', this)" title="Why was this shown?">Why?</button>
            <button class="btn ghost-btn small dismiss" onclick="dismissJob('{fp}', this)" title="Not for me — hide and learn">×</button>
          </div>
        </div>""")

    # Derive a subtitle from the user's AI skills profile (industry-aware).
    if SKILLS_PROFILE:
        primary = (SKILLS_PROFILE.get("primaryRole") or "").strip()
        remote_pref = "Remote" if SKILLS_PROFILE.get("remotePreferred") else "On-site or remote"
        subtitle = (primary + " · " + remote_pref) if primary else remote_pref
    else:
        subtitle = "Awaiting resume upload — click Resume to get started"

    # Friendlier empty-state message depending on why we have 0 cards
    if cards:
        cards_html = "\n".join(cards)
    elif SKILLS_PROFILE and user_industries:
        cards_html = (
            f"<div style='padding:32px;max-width:640px;margin:30px auto;background:#fff;"
            f"border:1px solid #e2e5ea;border-radius:8px;line-height:1.55;'>"
            f"<h3 style='margin:0 0 10px 0;color:#5C5CD6;'>No matching jobs yet for {_esc(user_name)}</h3>"
            f"<p style='color:#555;font-size:14px;'>Your profile industries: "
            f"<strong>{_esc(', '.join(user_industries[:5]))}</strong>. "
            f"We haven't indexed companies in these industries yet. "
            f"Ask the admin to add relevant companies, or click <em>Resume</em> to update your profile.</p></div>"
        )
    elif not SKILLS_PROFILE:
        cards_html = (
            f"<div style='padding:32px;max-width:640px;margin:30px auto;background:#fff;"
            f"border:1px solid #e2e5ea;border-radius:8px;line-height:1.55;'>"
            f"<h3 style='margin:0 0 10px 0;color:#5C5CD6;'>Welcome, {_esc(user_name)}!</h3>"
            f"<p style='color:#555;font-size:14px;'>Click the <strong>Resume</strong> button (top-right) and "
            f"upload your resume as PDF or Word. The AI will read it and start matching jobs to your background. "
            f"Your tailored dashboard will appear here after the next refresh.</p></div>"
        )
    else:
        cards_html = "<p style='padding:24px;color:#666;'>No matches in the last 30 days. Click Refresh data to look again.</p>"

    html = HTML_TEMPLATE.format(
        total=total,
        senior_remote=senior_remote,
        ghost=ghost,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        shown=len(rows),
        cards=cards_html,
        user_slug=user_slug,
        user_name=_esc(user_name),
        subtitle=_esc(subtitle),
        has_profile_js=("true" if SKILLS_PROFILE else "false"),
    )
    # Some embedded emoji in HTML_TEMPLATE are stored as UTF-16 surrogate
    # pair literals (\ud83c\udfaf etc). Merge them into proper codepoints
    # so the output is valid UTF-8 (the browser refuses to parse JS that
    # contains lone surrogate bytes, which would silently break every
    # onclick on the page including the Preferences button).
    import re as _re
    def _merge_surrogates(s):
        return _re.sub(
            r"[\ud800-\udbff][\udc00-\udfff]",
            lambda m: chr(0x10000 + (ord(m.group(0)[0]) - 0xd800) * 0x400 + (ord(m.group(0)[1]) - 0xdc00)),
            s,
        )
    html = _merge_surrogates(html)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDashboard written: {output_path}")


def generate_all_dashboards(conn):
    """Generate one dashboard per user in users.json.

    Note: index.html is the public-facing landing page (getmemyjob marketing
    page), NOT a dashboard. Users access their dashboards directly at
    /<slug>.html (e.g. /geetu.html for Geetanjali). This refresh job does not
    touch index.html or landing.html.
    """
    # Ensure COMPANY_INDUSTRIES is built (may not have been if called standalone)
    if not COMPANY_INDUSTRIES:
        try:
            with open(COMPANIES_PATH) as f:
                _build_company_industries(json.load(f))
        except Exception as e:
            print(f"[industries] could not load companies.json: {e}", flush=True)
    users = load_users()
    print(f"\n[multi-user] generating dashboards for {len(users)} users")
    for user in users:
        slug = user["slug"]
        name = user.get("name", slug)
        out = os.path.join(ROOT, f"{slug}.html")
        generate_dashboard(conn, user_slug=slug, user_name=name, output_path=out)


def _days_old(iso):
    if not iso: return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Jobs for {user_name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="theme-color" content="#5C5CD6">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="icon" type="image/png" sizes="256x256" href="favicon.png">
<link rel="apple-touch-icon" href="favicon.png">
<meta name="description" content="A curated, AI-matched job feed for senior leadership roles — by OfficeBeat LLC.">
<meta property="og:type" content="website">
<meta property="og:title" content="getmemyjob — your tailored job feed">
<meta property="og:description" content="Real openings from real companies, AI-matched to your skills. By OfficeBeat LLC.">
<meta property="og:image" content="https://getmyjob.officebeatllc.com/og-card.png">
<meta property="og:site_name" content="getmemyjob">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://getmyjob.officebeatllc.com/og-card.png">
<style>
  body {{ font: 14px -apple-system, system-ui, sans-serif; margin: 0; background: #f7f7f8; color: #222; }}
  header {{ background: #5C5CD6; color: white; padding: 18px 28px; position: relative; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .sub {{ opacity: .85; font-size: 13px; margin-top: 4px; }}
  .header-actions {{ position: absolute; right: 28px; top: 50%; transform: translateY(-50%); display: flex; gap: 8px; }}
  .header-btn {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }}
  .header-btn:hover {{ background: rgba(255,255,255,0.25); }}
  .header-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
  .stats {{ display: flex; gap: 24px; padding: 14px 28px; background: white; border-bottom: 1px solid #e5e5ea; }}
  .stat {{ font-size: 13px; }}
  .goal-stat {{ background: linear-gradient(135deg, #f8f4ff 0%, #eef0ff 100%) !important; }}
  .goal-stat b {{ color: #5C5CD6 !important; }}
  .stat b {{ font-size: 22px; display: block; color: #5C5CD6; }}
  .filters {{ padding: 12px 28px; background: white; border-bottom: 1px solid #e5e5ea; display: flex; gap: 12px; }}
  .filters input, .filters select {{ padding: 6px 10px; font-size: 13px; border: 1px solid #ddd; border-radius: 6px; }}
  .grid {{ padding: 18px 28px; display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 14px; }}
  .card {{ background: white; border-radius: 10px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .row1 {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
  .title a {{ color: #5C5CD6; text-decoration: none; font-weight: 600; font-size: 15px; }}
  .title a:hover {{ text-decoration: underline; }}
  .score {{ background: #5C5CD6; color: white; border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600; }}
  .row2 {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .badges {{ margin: 8px 0; display: flex; flex-wrap: wrap; gap: 6px; }}
  .b {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; }}
  .b.senior {{ background: #e6f0ff; color: #5C5CD6; }}
  .b.remote {{ background: #e6fff0; color: #0a6b3a; }}
  .b.contract {{ background: #f3e6ff; color: #5a1f8a; }}
  .b.ghost {{ background: #fff1e6; color: #a85c00; }}
  .b.repost {{ background: #ffe6e6; color: #a80000; }}
  .b.fresh {{ background: #fffbe6; color: #8a6d00; font-weight: 600; }}
  .b.week {{ background: #f0e6ff; color: #4b2e9c; }}
  .pill {{ font-size: 12px; padding: 5px 12px; border-radius: 999px; border: 1px solid #ddd; background: white; cursor: pointer; }}
  .pill.active {{ background: #5C5CD6; color: white; border-color: #5C5CD6; }}
  .actions {{ margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }}
  .btn {{ font-size: 12px; padding: 6px 10px; border-radius: 6px; border: 1px solid #ddd; background: white; cursor: pointer; color: #333; text-decoration: none; display: inline-block; }}
  .btn:hover {{ background: #f0f0f0; }}
  .btn.primary {{ background: #5C5CD6; color: white; border-color: #5C5CD6; }}
  .btn.primary:hover {{ background: #4B4BBE; }}
  .btn.track.applied {{ background: #0a6b3a; color: white; border-color: #0a6b3a; }}
  .btn.track.phonescreen {{ background: #c97a00; color: white; border-color: #c97a00; }}
  .btn.track.onsite {{ background: #7a009c; color: white; border-color: #7a009c; }}
  .btn.track.offer {{ background: #ff7700; color: white; border-color: #ff7700; }}
  .btn.track.rejected {{ background: #888; color: white; border-color: #888; }}
  .b.applied {{ background: #d6f5e3; color: #0a6b3a; }}
  .b.phonescreen {{ background: #fce5b8; color: #6b4500; }}
  .b.onsite {{ background: #ead4ff; color: #4b2e9c; }}
  .b.offer {{ background: #ffd9b3; color: #a04500; }}
  .b.rejected {{ background: #e8e8e8; color: #666; }}
  .app-tracker {{ padding: 14px 28px; background: white; border-bottom: 1px solid #e5e5ea; }}
  .view-toggle {{ display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }}
  .view-toggle .pill {{ font-size: 13px; padding: 6px 14px; }}
  .view-label {{ font-size: 12px; color: #666; margin-right: 4px; font-weight: 600; }}
  .app-stats {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .app-stat {{ font-size: 12px; padding: 8px 14px; border-radius: 8px; min-width: 80px; }}
  .app-stat b {{ font-size: 20px; display: block; font-weight: 700; line-height: 1.15; }}
  .app-stat.applied {{ background: #d6f5e3; color: #0a6b3a; }}
  .app-stat.phonescreen {{ background: #fce5b8; color: #6b4500; }}
  .app-stat.onsite {{ background: #ead4ff; color: #4b2e9c; }}
  .app-stat.offer {{ background: #ffd9b3; color: #a04500; }}
  .app-stat.rejected {{ background: #e8e8e8; color: #666; }}
  .app-stat.response {{ background: #5C5CD6; color: white; }}
  body.apps-mode .card[data-status="offer"] {{ order: 1; }}
  body.apps-mode .card[data-status="onsite"] {{ order: 2; }}
  body.apps-mode .card[data-status="phonescreen"] {{ order: 3; }}
  body.apps-mode .card[data-status="applied"] {{ order: 4; }}
  body.apps-mode .card[data-status="rejected"] {{ order: 5; }}
  .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; align-items: center; justify-content: center; padding: 20px; }}
  .modal-overlay.show {{ display: flex; }}
  .modal {{ background: white; border-radius: 12px; padding: 24px; max-width: 600px; width: 100%; max-height: 80vh; overflow-y: auto; }}
  .modal h3 {{ margin: 0 0 12px 0; color: #5C5CD6; }}
  .modal pre {{ background: #f5f5f5; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }}
  .modal .copy-btn {{ margin-top: 10px; }}
  .modal-close {{ float: right; cursor: pointer; font-size: 22px; line-height: 1; color: #999; }}
  .prep-result-modal {{ max-width: 760px; }}
  .prep-status {{ font-size: 13px; color: #555; padding: 14px 0; }}
  .prep-status.error {{ color: #a80000; }}
  .prep-section {{ margin: 18px 0; padding-bottom: 18px; border-bottom: 1px solid #eee; }}
  .prep-section:last-child {{ border-bottom: none; }}
  .prep-label {{ font-size: 12px; font-weight: 700; color: #5C5CD6; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
  .prep-text {{ background: #f7f7f8; padding: 12px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; font-family: inherit; max-height: 260px; overflow-y: auto; margin: 0 0 8px 0; }}
  .desc {{ font-size: 12.5px; color: #444; margin-top: 6px; line-height: 1.4; }}
  .salary-row {{ margin: 6px 0 2px 0; }}
  .salary {{ display: inline-block; background: #e6fff0; color: #0a6b3a; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
  .tabs {{ display: flex; gap: 4px; border-bottom: 1px solid #e0e0e0; margin: 10px 0 16px 0; }}
  .tab-btn {{ background: none; border: none; padding: 8px 14px; cursor: pointer; font-size: 13px; color: #666; border-bottom: 2px solid transparent; font-weight: 500; }}
  .tab-btn.active {{ color: #5C5CD6; border-bottom-color: #5C5CD6; font-weight: 700; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .dropzone {{ display: block; box-sizing: border-box; width: 100%; border: 2px dashed #c0c8d4; border-radius: 8px; padding: 28px 16px; text-align: center; background: #fafbfc; transition: all 0.15s; cursor: pointer; }}
  .dropzone:hover, .dropzone.drag {{ background: #eef3fa; border-color: #5C5CD6; }}
  .dropzone strong {{ display: block; font-size: 14px; color: #5C5CD6; margin-bottom: 4px; }}
  .dropzone span {{ display: block; font-size: 12px; color: #666; }}
  .version-row {{ display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid #e6e8eb; border-radius: 6px; margin-bottom: 6px; background: #fff; }}
  .version-row.active {{ border-color: #5C5CD6; background: #f3f7fc; }}
  .version-main {{ flex: 1; min-width: 0; }}
  .version-label {{ font-weight: 600; font-size: 13px; color: #5C5CD6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .version-meta {{ font-size: 11px; color: #777; margin-top: 2px; }}
  .version-badge {{ background: #5C5CD6; color: white; font-size: 10px; padding: 2px 7px; border-radius: 10px; font-weight: 700; letter-spacing: 0.3px; }}
  .version-actions {{ display: flex; gap: 4px; }}
  .v-btn {{ background: #f3f4f6; border: 1px solid #ddd; color: #333; padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: 500; }}
  .v-btn:hover {{ background: #e6e8eb; }}
  .v-btn.danger {{ color: #b00; }}
  .v-btn.primary {{ background: #5C5CD6; color: white; border-color: #5C5CD6; }}
  /* LinkedIn contacts feature */
  .contact-badge {{ display: inline-flex; align-items: center; gap: 4px; background: #eaf2fb; color: #0a66c2; border: 1px solid #c9defb; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; cursor: pointer; margin-left: 8px; transition: all 0.12s; }}
  .contact-badge:hover {{ background: #d8e7f8; border-color: #0a66c2; }}
  .contact-badge.hiring {{ background: #fff3d6; color: #b85c00; border-color: #f0c47a; }}
  .contact-badge.hiring:hover {{ background: #ffe7a8; }}
  .btn.pending-confirm {{ background: #fff3d6 !important; color: #b85c00 !important; border-color: #f0c47a !important; }}
  .contact-badge .ic {{ font-size: 12px; line-height: 1; }}
  .contact-row {{ display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border: 1px solid #e6e8eb; border-radius: 8px; margin-bottom: 10px; background: #fff; }}
  .contact-row .name-line {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }}
  .contact-row .cname {{ font-weight: 700; color: #5C5CD6; font-size: 14px; }}
  .contact-row .ctitle {{ font-size: 12px; color: #555; }}
  .contact-row .cmeta {{ font-size: 11px; color: #888; }}
  .contact-row .crow-actions {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }}
  .contact-row .msg-box {{ background: #f7f9fc; border: 1px solid #e2e7ef; border-radius: 6px; padding: 10px 12px; font-size: 12.5px; line-height: 1.55; color: #1f2a3a; white-space: pre-wrap; font-family: ui-sans-serif, system-ui, sans-serif; margin-top: 6px; }}
  .contact-empty {{ padding: 18px; text-align: center; color: #777; font-size: 13px; }}
  .contact-summary {{ background:#f3f7fc; border:1px solid #d6e1f1; border-radius:8px; padding:10px 14px; font-size:12px; color:#5C5CD6; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; }}
  .contact-summary .clear-btn {{ background: transparent; border: 1px solid #c9defb; color: #0a66c2; padding: 3px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; }}
  .contact-summary .clear-btn:hover {{ background: #fff; }}
  /* ---- First-login wizard ---- */
  .wiz-overlay {{ position: fixed; inset: 0; background: rgba(15,23,60,0.92); z-index: 1000; display: none; align-items: center; justify-content: center; padding: 24px; }}
  .wiz-overlay.show {{ display: flex; }}
  .wiz-card {{ background: #fff; border-radius: 14px; max-width: 560px; width: 100%; max-height: 88vh; overflow-y: auto; box-shadow: 0 24px 64px rgba(0,0,0,0.35); padding: 30px 34px 26px; }}
  .wiz-step-count {{ font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #5C6BC0; margin-bottom: 10px; }}
  .wiz-progress {{ display: flex; gap: 6px; margin-bottom: 22px; }}
  .wiz-progress .dot {{ width: 28px; height: 4px; border-radius: 2px; background: #E2E2F2; }}
  .wiz-progress .dot.done {{ background: #5C6BC0; }}
  .wiz-progress .dot.active {{ background: #5C5CD6; }}
  .wiz-title {{ font-size: 24px; font-weight: 700; color: #5C5CD6; margin: 0 0 10px 0; line-height: 1.2; }}
  .wiz-body {{ font-size: 14.5px; color: #333; line-height: 1.55; margin: 0 0 22px 0; }}
  .wiz-body p {{ margin: 0 0 10px 0; }}
  .wiz-body ul {{ padding-left: 20px; margin: 8px 0; }}
  .wiz-body li {{ margin-bottom: 4px; }}
  .wiz-body strong {{ color: #5C5CD6; }}
  .wiz-actions {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .wiz-btn-primary {{ background: #5C5CD6; color: #fff; border: none; padding: 11px 22px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }}
  .wiz-btn-primary:hover {{ background: #4B4BBE; }}
  .wiz-btn-ghost {{ background: transparent; color: #666; border: none; padding: 11px 14px; font-size: 13.5px; cursor: pointer; }}
  .wiz-btn-ghost:hover {{ color: #5C5CD6; text-decoration: underline; }}
  .wiz-skip {{ margin-left: auto; }}
  .wiz-help-btn {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; width: 32px; height: 32px; border-radius: 50%; font-size: 14px; font-weight: 700; cursor: pointer; padding: 0; display: inline-flex; align-items: center; justify-content: center; }}
  .wiz-help-btn:hover {{ background: rgba(255,255,255,0.28); }}
  .recovery-overlay {{ position: fixed; inset: 0; background: rgba(15,23,60,0.9); z-index: 1100; display: none; align-items: center; justify-content: center; padding: 24px; }}
  .recovery-overlay.show {{ display: flex; }}
  .recovery-card {{ background: #fff; border-radius: 14px; padding: 28px 32px; max-width: 520px; width: 100%; box-shadow: 0 24px 60px rgba(0,0,0,0.3); }}
  .recovery-card h3 {{ margin: 0 0 12px 0; color: #5C5CD6; font-size: 22px; }}
  .recovery-card p {{ margin: 0 0 14px 0; line-height: 1.5; font-size: 14px; color: #333; }}
  .recovery-row {{ margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }}
  .recovery-btn {{ background: #5C5CD6; color: white; border: 0; padding: 10px 18px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
  .recovery-btn:hover {{ background: #4848bf; }}
  .recovery-btn.ghost {{ background: #fff; color: #5C5CD6; border: 1px solid #c0c8d4; }}
  .recovery-input {{ width: 100%; padding: 10px 12px; border: 1px solid #c0c8d4; border-radius: 8px; font-size: 13px; margin-top: 8px; box-sizing: border-box; font-family: monospace; }}
  .recovery-status {{ font-size: 12px; color: #777; margin-top: 10px; min-height: 16px; }}
  .recovery-status.ok {{ color: #0a6b3a; }}
  .recovery-status.err {{ color: #b00; }}
  .wiz-banner {{ position: fixed; top: 80px; left: 50%; transform: translateX(-50%); background: #5C5CD6; color: #fff; padding: 14px 22px; border-radius: 8px; box-shadow: 0 6px 20px rgba(0,0,0,0.25); z-index: 200; font-size: 14px; font-weight: 500; max-width: 90%; text-align: center; }}

  /* ---- Mobile responsive ---- */
  @media (max-width: 640px) {{
    header {{ padding: 14px 16px; }}
    header h1 {{ font-size: 18px; }}
    header .sub {{ font-size: 12px; }}
    .header-actions {{ position: static; transform: none; margin-top: 12px; flex-wrap: wrap; gap: 6px; }}
    .header-btn {{ padding: 8px 12px; font-size: 12.5px; flex: 0 0 auto; }}
    .wiz-help-btn {{ width: 30px; height: 30px; font-size: 13px; }}
    .stats {{ gap: 12px; padding: 12px 16px; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    .stat {{ flex: 0 0 auto; min-width: 84px; font-size: 11.5px; }}
    .stat b {{ font-size: 18px; }}
    .filters {{ padding: 10px 16px; gap: 8px; flex-wrap: wrap; }}
    .filters input, .filters select {{ font-size: 13px; padding: 8px 10px; flex: 1 1 140px; }}
    .grid {{ padding: 14px 16px; grid-template-columns: 1fr; gap: 10px; }}
    .card {{ padding: 12px; }}
    .title a {{ font-size: 14.5px; }}
    .app-tracker {{ padding: 12px 16px; }}
    .view-toggle {{ flex-wrap: wrap; }}
    .view-toggle .pill {{ font-size: 12px; padding: 7px 12px; }}
    .app-stats {{ gap: 8px; }}
    .app-stat {{ min-width: 68px; padding: 6px 10px; font-size: 11px; }}
    .app-stat b {{ font-size: 16px; }}
    .modal-overlay {{ padding: 0; }}
    .modal {{ max-width: 100%; max-height: 100vh; height: 100vh; border-radius: 0; padding: 18px 16px; }}
    .tabs {{ overflow-x: auto; -webkit-overflow-scrolling: touch; flex-wrap: nowrap; }}
    .tab-btn {{ padding: 10px 12px; font-size: 13px; flex: 0 0 auto; min-height: 44px; }}
    .btn {{ padding: 9px 12px; font-size: 13px; min-height: 38px; }}
    .pill {{ padding: 7px 14px; min-height: 38px; }}
    .wiz-card {{ padding: 22px 20px 18px; border-radius: 10px; max-height: 92vh; }}
    .wiz-title {{ font-size: 20px; }}
    .wiz-body {{ font-size: 14px; }}
    .wiz-btn-primary {{ padding: 12px 18px; width: 100%; }}
    .wiz-actions {{ flex-direction: column; align-items: stretch; gap: 6px; }}
    .wiz-skip {{ margin-left: 0; text-align: center; }}
    .wiz-banner {{ top: auto; bottom: 16px; left: 16px; right: 16px; transform: none; max-width: none; font-size: 13.5px; padding: 12px 16px; }}
    .contact-row {{ padding: 10px 12px; }}
    .contact-row .msg-box {{ font-size: 12px; padding: 8px 10px; }}
  }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
</head><body>

<!-- Access-recovery modal: shown when an auth-required action returns 401 -->
<div class="recovery-overlay" id="recovery-modal" role="dialog" aria-modal="true" aria-labelledby="recovery-title">
  <div class="recovery-card">
    <h3 id="recovery-title">Your access key isn\'t valid anymore</h3>
    <p>This usually happens after clearing cookies or switching browsers. Two ways to get back in:</p>
    <p style="font-weight: 600; color: #5C5CD6;">Option A — paste a fresh invite URL</p>
    <p style="font-size: 13px; color: #555;">If you saved the original invite email or text message, paste the full URL below (it ends with <code>?key=&hellip;</code>):</p>
    <input id="recovery-paste-input" class="recovery-input" type="text" placeholder="https://getmemyjob.officebeatllc.com/{user_slug}.html?key=&hellip;">
    <div class="recovery-row">
      <button class="recovery-btn" onclick="recoveryApplyPaste()">Apply &amp; retry</button>
    </div>
    <div id="recovery-paste-status" class="recovery-status"></div>
    <p style="margin-top: 22px; font-weight: 600; color: #5C5CD6;">Option B — email Amit for a new link</p>
    <p style="font-size: 13px; color: #555;">If you don\'t have the original link, this opens your email app pre-filled. Amit will resend a fresh invite from the admin panel.</p>
    <div class="recovery-row">
      <a class="recovery-btn" id="recovery-mailto" href="#">Email Amit for a new invite</a>
      <button class="recovery-btn ghost" onclick="recoveryHide()">Close</button>
    </div>
  </div>
</div>

<!-- First-login wizard overlay -->
<div class="wiz-overlay" id="gmj-wizard" role="dialog" aria-modal="true" aria-labelledby="wiz-title">
  <div class="wiz-card">
    <div class="wiz-step-count" id="wiz-step-count">Step 1 of 5</div>
    <div class="wiz-progress" id="wiz-progress"></div>
    <h2 class="wiz-title" id="wiz-title">Welcome</h2>
    <div class="wiz-body" id="wiz-body"></div>
    <div class="wiz-actions">
      <button class="wiz-btn-primary" id="wiz-cta" type="button">Let's go</button>
      <button class="wiz-btn-ghost" id="wiz-save-exit" type="button" style="display:none">Save &amp; exit</button>
      <button class="wiz-btn-ghost" id="wiz-back" type="button" style="display:none">Back</button>
      <button class="wiz-btn-ghost wiz-skip" id="wiz-skip" type="button">Skip for now</button>
    </div>
  </div>
</div>

<header>
  <h1>Jobs for {user_name}</h1>
  <div class="sub">{subtitle} · Generated {generated}</div>
  <div class="header-actions">
    <button class="header-btn" onclick="window.location.href='/?force=1'" title="Sign out and switch to a different dashboard">Switch user</button>
    <button id="prefs-btn" class="header-btn" onclick="replayTour()" title="Re-open the setup wizard to change your locations, remote pref, and company sizes">Preferences</button>
    <button id="regen-btn" class="header-btn" onclick="regenerateFromHeader(this)" title="Re-run the AI matcher to refresh your suggested target companies and skills. Takes 30-60 seconds.">Regenerate matches</button>
    <button id="resume-btn" class="header-btn" onclick="openResumeModal()">Resume</button>
    <button id="contacts-btn" class="header-btn" onclick="openContactsModal()">LinkedIn Contacts</button>
    <button id="refresh-btn" class="header-btn" onclick="refreshData()">Refresh data</button>
  </div>
</header>
<div class="stats">
  <div class="stat"><b>{total}</b>Total jobs tracked</div>
  <div class="stat"><b>{senior_remote}</b>Senior + Remote (last 7d)</div>
  <div class="stat"><b>{ghost}</b>Possible ghost jobs (60d+)</div>
  <div class="stat"><b id="shown-counter">{shown}</b>Showing</div>
  <div class="stat goal-stat" id="goal-stat">
    <b><span id="goal-today-count">0</span>/<span id="goal-today-target">5</span></b>
    <span>Today\u2019s applications<br><span id="goal-progress-bar" style="display:inline-block;width:90%;height:5px;background:#e6e8eb;border-radius:3px;margin-top:4px;overflow:hidden;"><span id="goal-progress-fill" style="display:block;height:100%;width:0%;background:#5C5CD6;border-radius:3px;transition:width 0.3s;"></span></span> <span id="goal-streak" style="font-size:11px;color:#777;margin-left:4px;"></span></span>
  </div>
</div>
<div class="app-tracker">
  <div class="view-toggle">
    <span class="view-label">View:</span>
    <button class="pill active" id="view-all" onclick="setView('all')">All Jobs</button>
    <button class="pill" id="view-apps" onclick="setView('apps')">My Applications</button>
    <span class="view-label" style="margin-left:20px;">Type:</span>
    <button class="pill active" id="type-all" onclick="setEmploymentFilter('all')">All</button>
    <button class="pill" id="type-fulltime" onclick="setEmploymentFilter('full-time')">Full-time</button>
    <button class="pill" id="type-contract" onclick="setEmploymentFilter('contract')">Contract</button>
  </div>
  <div id="funnel-row" style="display:flex; gap:6px; align-items:stretch; margin-top:4px;"></div>
  <!-- Hidden per-status counters (used by JS) -->
  <div style="display:none;">
    <span id="cnt-applied">0</span><span id="cnt-phonescreen">0</span><span id="cnt-onsite">0</span>
    <span id="cnt-offer">0</span><span id="cnt-rejected">0</span><span id="cnt-response">--</span>
  </div>
</div>
<div class="filters">
  <input type="text" id="q" placeholder="Search title or company…" oninput="filter()">
  <select id="srOnly" onchange="filter()">
    <option value="">All jobs</option>
    <option value="srOnly">Senior + Remote only</option>
    <option value="sOnly">Senior only</option>
    <option value="rOnly">Remote only</option>
  </select>
  <select id="trackedFilter" onchange="filter()">
    <option value="">Tracker: all</option>
    <option value="untouched">Not yet applied</option>
    <option value="applied">Applied</option>
    <option value="phonescreen">Phone screen</option>
    <option value="onsite">Onsite</option>
    <option value="offer">Offer</option>
    <option value="rejected">Rejected</option>
  </select>
  <select id="salaryFilter" onchange="filter()">
    <option value="">Salary: any</option>
    <option value="listed">With salary listed</option>
    <option value="100000">$100k+</option>
    <option value="150000">$150k+</option>
    <option value="200000">$200k+</option>
    <option value="250000">$250k+</option>
  </select>
  <select id="recruiterFilter" onchange="filter()" title="Show or hide jobs posted by staffing/recruiting agencies">
    <option value="hide" selected>Recruiters: Hide</option>
    <option value="show">Recruiters: Show</option>
    <option value="only">Recruiters: Only</option>
  </select>
  <select id="sortBy" onchange="sortCards()">
    <option value="score">Sort: Best match</option>
    <option value="salary">Sort: Salary (high to low)</option>
    <option value="recent">Sort: Most recent</option>
    <option value="ghost">Sort: Newest postings first</option>
  </select>
  <span style="display:flex; gap:6px; align-items:center;">
    <button class="pill active" data-window="all" onclick="setWindow(this,'all')">All</button>
    <button class="pill" data-window="0" onclick="setWindow(this,0)">Today</button>
    <button class="pill" data-window="7" onclick="setWindow(this,7)">Last 7 days</button>
    <button class="pill" data-window="14" onclick="setWindow(this,14)">Last 14 days</button>
    <button class="pill" data-window="30" onclick="setWindow(this,30)">Last 30 days</button>
  </span>
</div>
<div id="contacts-priority-indicator" style="margin: 0 0 12px 0; min-height: 18px;"></div>
<div class="grid" id="grid">
{cards}
</div>

<div class="modal-overlay" id="resume-modal" onclick="if(event.target===this)closeResumeModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeResumeModal()">&times;</span>
    <h3>{user_name}'s Resume</h3>
    <p class="prep-status" id="resume-status">Loading…</p>
    <div id="resume-editor" style="display:none;">
      <div class="tabs">
        <button class="tab-btn active" data-tab="upload" onclick="setResumeTab('upload')">Upload File</button>
        <button class="tab-btn" data-tab="profile" onclick="setResumeTab('profile')">My Profile</button>
        <button class="tab-btn" data-tab="versions" onclick="setResumeTab('versions')">Versions</button>
        <button class="tab-btn" data-tab="json" onclick="setResumeTab('json')">Edit JSON</button>
      </div>

      <div class="tab-panel active" id="tab-upload">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">Upload your resume as PDF or Word. The AI converts it to structured form and saves a new version.</p>
        <label for="resume-file-input" class="dropzone" id="resume-dropzone">
          <strong id="dropzone-label">Click to choose a file</strong>
          <span>or drop a PDF or Word file (.docx — not legacy .doc) here</span>
        </label>
        <input type="file" id="resume-file-input" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" style="display:none;">
        <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
          <button class="btn primary" id="parse-resume-btn" onclick="parseUploadedResume(this)" disabled>Parse &amp; Save</button>
          <span id="upload-status" style="font-size: 12px; color: #555;"></span>
        </div>
        <details style="margin-top:14px;font-size:12px;color:#666;">
          <summary style="cursor:pointer;">What happens?</summary>
          <ol style="margin:6px 0 0 18px;padding:0;line-height:1.6;">
            <li>Your browser reads the file locally (it never leaves your computer raw).</li>
            <li>The extracted text is sent to the Cloudflare Worker.</li>
            <li>Claude converts it to structured JSON, saved as a new version.</li>
            <li>The new version becomes active immediately.</li>
          </ol>
        </details>
      </div>

      <div class="tab-panel" id="tab-profile">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">This is what the AI extracted from your resume. We use it to match jobs. If something is missing, click <em>Edit</em> to add your own chips, or <em>Regenerate</em> to re-run extraction.</p>
        <div id="profile-display"><p style="font-size:12px;color:#888;">Loading profile…</p></div>
        <div id="profile-actions" style="margin-top:14px; display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn primary" id="edit-profile-btn" onclick="openEditProfileModal()">Edit profile</button>
          <button class="btn" id="regen-profile-btn" onclick="regenerateProfile(this)" style="background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;">Regenerate from resume</button>
          <span id="regen-profile-status" style="font-size: 12px; color: #555;"></span>
        </div>
      </div>

      <!-- Edit profile modal -->
      <div id="edit-profile-overlay" style="display:none; position:fixed; inset:0; background:rgba(20,30,50,0.45); z-index:60; align-items:center; justify-content:center;" onclick="if(event.target===this)closeEditProfileModal()">
        <div style="background:#fff; padding:24px 28px; border-radius:10px; max-width:640px; width:100%; margin:12px; max-height:88vh; overflow-y:auto; box-shadow:0 24px 60px rgba(0,0,0,0.2);">
          <h3 style="margin:0 0 6px 0; color:#5C5CD6;">Edit your profile</h3>
          <p style="font-size:13px; color:#555; margin:0 0 16px 0;">Each field is a comma-separated list. Add things the AI missed (e.g. NIST CSF, HIPAA, ISO 27001). Remove anything inaccurate. Saving updates the profile used for job matching.</p>
          <div id="edit-profile-fields"></div>
          <div style="margin-top:18px; display:flex; gap:8px; flex-wrap:wrap;">
            <button class="btn primary" onclick="saveProfileEdits()">Save changes</button>
            <button class="btn" onclick="closeEditProfileModal()" style="background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;">Cancel</button>
            <span id="edit-profile-status" style="font-size:12px;color:#555;align-self:center;"></span>
          </div>
        </div>
      </div>

      <div class="tab-panel" id="tab-versions">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">Older versions remain saved. Click <em>Activate</em> to switch which one the AI uses.</p>
        <div id="versions-list"><p style="font-size:12px;color:#888;">Loading versions…</p></div>
      </div>

      <div class="tab-panel" id="tab-json">
        <p style="font-size:13px;color:#555;margin-bottom:8px;">Advanced: paste structured JSON directly. Saving creates a new version.</p>
        <textarea id="resume-text" spellcheck="false" style="width:100%; height:300px; font-family: ui-monospace, Menlo, monospace; font-size: 12px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; resize: vertical;"></textarea>
        <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
          <button class="btn primary" onclick="saveResume(this)">Save resume</button>
          <span id="resume-save-status" style="font-size: 12px; color: #555;"></span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- LinkedIn Contacts modal -->
<div class="modal-overlay" id="contacts-modal" onclick="if(event.target===this)closeContactsModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeContactsModal()">&times;</span>
    <h3>LinkedIn Contacts</h3>
    <p style="font-size:13px;color:#555;margin:0 0 14px 0;">
      Upload your LinkedIn connections (CSV) and we'll show you which of your contacts work at the companies you're applying to. Each match comes with a draft outreach message you can copy and a one-click link to their profile.
    </p>
    <div id="contacts-summary-wrap"></div>
    <div class="tabs" style="margin-bottom:10px;">
      <button class="tab-btn active" data-ctab="upload" onclick="setContactsTab('upload')">Upload CSV</button>
      <button class="tab-btn" data-ctab="list" onclick="setContactsTab('list')">My Contacts</button>
      <button class="tab-btn" data-ctab="how" onclick="setContactsTab('how')">How to export</button>
    </div>

    <div class="tab-panel active" id="ctab-upload">
      <label for="contacts-file-input" class="dropzone" id="contacts-dropzone">
        <strong id="contacts-dropzone-label">Click to choose your Connections.csv</strong>
        <span>or drop the file here. Only stays in your browser — never uploaded.</span>
      </label>
      <input type="file" id="contacts-file-input" accept=".csv,text/csv" style="display:none;">
      <div style="margin-top:12px; display:flex; gap:8px; align-items:center;">
        <button class="btn primary" id="parse-contacts-btn" onclick="parseUploadedContacts(this)" disabled>Save contacts</button>
        <span id="contacts-upload-status" style="font-size:12px; color:#555;"></span>
      </div>
    </div>

    <div class="tab-panel" id="ctab-list">
      <div id="contacts-list-wrap"><p class="contact-empty">No contacts saved yet. Upload your Connections.csv on the first tab.</p></div>
    </div>

    <div class="tab-panel" id="ctab-how">
      <ol style="font-size:13px; line-height:1.7; color:#333; padding-left:20px;">
        <li>Open LinkedIn → click your photo (top right) → <b>Settings &amp; Privacy</b>.</li>
        <li>Go to <b>Data Privacy</b> → <b>Get a copy of your data</b>.</li>
        <li>Choose <b>Want something in particular?</b> → check <b>Connections</b> only (faster than full archive).</li>
        <li>Click <b>Request archive</b>. LinkedIn emails you a download link, usually within 10 minutes.</li>
        <li>Open the email, download the ZIP, unzip it, and find <b>Connections.csv</b> inside.</li>
        <li>Come back here and upload that file on the <b>Upload CSV</b> tab.</li>
      </ol>
      <p style="font-size:12px; color:#777; margin-top:14px; line-height:1.6;">
        Re-upload anytime to refresh — newer uploads replace older ones. The file is parsed in your browser and stored only on this device.
      </p>
    </div>
  </div>
</div>

<div class="modal-overlay" id="company-contacts-modal" onclick="if(event.target===this)closeCompanyContactsModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeCompanyContactsModal()">&times;</span>
    <h3 id="company-contacts-title">Contacts at company</h3>
    <p style="font-size:13px;color:#555;margin:0 0 14px 0;" id="company-contacts-sub">Here are people you know who work there.</p>
    <div id="company-contacts-list"></div>
  </div>
</div>

<div class="modal-overlay" id="prep-modal" onclick="if(event.target===this)closeModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeModal()">&times;</span>
    <h3 id="prep-modal-title">Prep this application</h3>
    <p id="prep-status" class="prep-status">Generating tailored materials with Claude…</p>
    <div id="prep-output" style="display:none;">
      <div class="prep-section">
        <div class="prep-label">Resume Summary</div>
        <pre id="prep-summary" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-summary', this)">Copy summary</button>
      </div>
      <div class="prep-section">
        <div class="prep-label">Cover Letter</div>
        <pre id="prep-cover" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-cover', this)">Copy cover letter</button>
      </div>
      <div class="prep-section">
        <div class="prep-label">LinkedIn Intro</div>
        <pre id="prep-linkedin" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-linkedin', this)">Copy LinkedIn intro</button>
      </div>
      <div class="prep-section" id="prep-resume-section" style="display:none;">
        <div class="prep-label">Tailored Resume</div>
        <div id="prep-resume-preview" style="background:#fff; border:1px solid #e2e5ea; padding:18px 22px; border-radius:6px; font-size:13px; line-height:1.5; max-height:420px; overflow-y:auto; margin:0 0 8px 0;"></div>
        <div style="display:flex; flex-wrap:wrap; gap:6px;">
          <button class="btn primary" onclick="copyTailoredResume(this)">Copy as text</button>
          <button class="btn primary" onclick="downloadTailoredResume('pdf', this)">Download PDF</button>
          <button class="btn primary" onclick="downloadTailoredResume('doc', this)">Download Word</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Application detail side panel -->
<div class="modal-overlay" id="app-detail-modal" onclick="if(event.target===this)closeAppDetail()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeAppDetail()">&times;</span>
    <h3 id="app-detail-title">Application details</h3>
    <div id="app-detail-body"><p style="color:#666; font-size:13px;">Loading…</p></div>
  </div>
</div>

<!-- Follow-up draft modal -->
<div class="modal-overlay" id="followup-modal" onclick="if(event.target===this)closeFollowupModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeFollowupModal()">&times;</span>
    <h3 id="followup-title">Draft follow-up email</h3>
    <p class="prep-status" id="followup-status">Generating with Claude…</p>
    <div id="followup-output" style="display:none;">
      <div class="prep-section">
        <div class="prep-label">Subject</div>
        <pre id="followup-subject" class="prep-text"></pre>
      </div>
      <div class="prep-section">
        <div class="prep-label">Body</div>
        <pre id="followup-body" class="prep-text"></pre>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
          <button class="btn primary" onclick="copyFollowupBody(this)">Copy</button>
          <button class="btn primary" onclick="openFollowupMailto()">Open in email client</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Interview prep modal -->
<div class="modal-overlay" id="interview-modal" onclick="if(event.target===this)closeInterviewModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeInterviewModal()">&times;</span>
    <h3 id="interview-title">Interview prep</h3>
    <p class="prep-status" id="interview-status">Generating with Claude… this takes 20-30 seconds.</p>
    <div id="interview-output" style="display:none;"></div>
  </div>
</div>

<script>
// === Identity + Worker base — MUST be first; everything below references USER_SLUG ===
const WORKER_BASE = 'https://cool-darkness-dce5.tr6jz6v7wg.workers.dev';
const USER_SLUG = '{user_slug}';
const USER_QS = '?user=' + encodeURIComponent(USER_SLUG);

// Remember this user as the most-recently-used dashboard so the root URL
// can auto-redirect them here next time.
try {{ localStorage.setItem('gmj_last_user', USER_SLUG); }} catch (e) {{}}

const RECENCY_WINDOW_KEY = 'htj_recency_window_' + USER_SLUG;
let activeWindow = (function() {{
  try {{ const v = localStorage.getItem(RECENCY_WINDOW_KEY); return v === null ? '7' : v; }} catch (e) {{ return '7'; }}
}})();

// --- Tracker state (localStorage) -----------------------------------------
const STATUS_CYCLE = ['', 'applied', 'phonescreen', 'onsite', 'offer', 'rejected'];
const STATUS_LABEL = {{
  '': 'Mark Applied',
  'applied': 'Applied ✓',
  'phonescreen': 'Phone Screen',
  'onsite': 'Onsite',
  'offer': 'Offer',
  'rejected': 'Rejected'
}};

// Tracker is server-side (Cloudflare KV). We cache it in memory for fast reads;
// every write goes to the Worker.
const TRACKER_WORKER_URL = WORKER_BASE + '/tracker' + USER_QS;
const FOLLOWUP_WORKER_URL = WORKER_BASE + '/draft-followup' + USER_QS;
const INTERVIEW_WORKER_URL = WORKER_BASE + '/interview-prep' + USER_QS;
let _trackerCache = null;

async function loadTracker(force) {{
  if (_trackerCache && !force) return _trackerCache;
  try {{
    const r = await fetch(TRACKER_WORKER_URL);
    const data = await r.json();
    _trackerCache = data.tracker || {{}};
  }} catch (e) {{
    // Fall back to localStorage if Worker unreachable
    try {{ _trackerCache = JSON.parse(localStorage.getItem('htj_tracker') || '{{}}'); }}
    catch (e2) {{ _trackerCache = {{}}; }}
  }}
  return _trackerCache;
}}

function getTracker() {{ return _trackerCache || {{}}; }}
function getStatus(fp) {{ return getTracker()[fp]?.status || ''; }}

async function _trackerAction(action, payload) {{
  const editKey = getEditKey();
  if (!editKey) return null;
  const body = Object.assign({{ action }}, payload || {{}});
  try {{
    const r = await fetch(TRACKER_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify(body),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
      return null;
    }}
    return data;
  }} catch (e) {{ alert('Network error: ' + (e.message || e)); return null; }}
}}

// One-click apply: open the job listing in a new tab and STASH it as a
// pending-confirm. We don't auto-mark Applied — that would inflate the
// counter for jobs the user just browses. Instead we ask them later
// (immediately if they tab back here, or on next dashboard load):
// "Did you complete your application to <Job> at <Company>?"
const PENDING_APPLY_KEY = "htj_pending_apply_" + USER_SLUG;

function _readPendingApplies() {{
  try {{ const r = localStorage.getItem(PENDING_APPLY_KEY); return r ? JSON.parse(r) : []; }} catch (e) {{ return []; }}
}}
function _writePendingApplies(arr) {{
  try {{ localStorage.setItem(PENDING_APPLY_KEY, JSON.stringify(arr.slice(0, 50))); }} catch (e) {{}}
}}

async function applyAndOpen(fp, btn, url) {{
  // Open immediately (before any await) so popup blockers don't kick in.
  try {{ window.open(url, "_blank", "noopener,noreferrer"); }} catch (e) {{}}
  // Stash a pending entry — we'll ask the user "did you finish?" shortly.
  const card = btn.closest(".card");
  const jobMeta = card ? {{
    fp: fp,
    title: (card.querySelector(".title a")?.textContent || "").trim(),
    company: (card.querySelector(".company")?.textContent || "").trim(),
    url: url,
    openedAt: new Date().toISOString(),
  }} : {{ fp: fp, title: "", company: "", url: url, openedAt: new Date().toISOString() }};
  const pending = _readPendingApplies().filter(p => p.fp !== fp);
  pending.push(jobMeta);
  _writePendingApplies(pending);
  // Visual cue on the button itself
  const orig = btn.textContent;
  btn.textContent = "Opened \u2192 confirm?";
  btn.disabled = false;
  btn.classList.add("pending-confirm");
  // Listen for tab refocus so we can prompt as soon as they come back
  setTimeout(function() {{ btn.textContent = orig; btn.classList.remove("pending-confirm"); }}, 8000);
  // Set up a one-shot prompt on next focus
  if (!window._pendingConfirmListenerAttached) {{
    window._pendingConfirmListenerAttached = true;
    window.addEventListener("focus", function() {{
      setTimeout(promptPendingApplies, 800);
    }});
  }}
  // Also schedule a prompt in 90s in case they don't come back to this tab
  setTimeout(promptPendingApplies, 90000);
}}

// Build a queue of unconfirmed apply-opens and prompt the user one at a time.
function promptPendingApplies() {{
  const pending = _readPendingApplies();
  if (!pending.length) return;
  // Already showing a prompt? Don't stack.
  if (document.getElementById("apply-confirm-modal")) return;
  const job = pending[0];
  const overlay = document.createElement("div");
  overlay.id = "apply-confirm-modal";
  overlay.className = "recovery-overlay show";
  overlay.style.zIndex = "1200";
  overlay.innerHTML =
    '<div class="recovery-card">' +
      '<h3 style="margin:0 0 6px 0;color:#5C5CD6;font-size:20px;">Did you finish applying?</h3>' +
      '<p style="margin:0 0 16px 0;color:#666;font-size:13px;">You opened <strong>' + (job.title || "this job") + '</strong>' + (job.company ? ' at <strong>' + job.company + '</strong>' : '') + '. Knowing whether you actually submitted lets us track your daily goal accurately.</p>' +
      '<div class="recovery-row">' +
        '<button class="recovery-btn" id="apply-confirm-yes">Yes \u2014 application submitted</button>' +
        '<button class="recovery-btn ghost" id="apply-confirm-no">No \u2014 skipped</button>' +
        '<button class="recovery-btn ghost" id="apply-confirm-later">Ask me later</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(overlay);

  function _finish(action) {{
    const arr = _readPendingApplies().filter(p => p.fp !== job.fp);
    _writePendingApplies(arr);
    overlay.remove();
    if (action === "applied") {{
      // Mark as applied via the tracker API
      _trackerAction("setStatus", {{ fp: job.fp, status: "applied", jobMeta: {{ title: job.title, company: job.company, url: job.url }} }})
        .then(function(r) {{
          if (r) _trackerCache[job.fp] = r.record;
          refreshTrackerUI();
          filter();
          if (typeof refreshDailyGoalWidget === "function") refreshDailyGoalWidget();
        }});
    }}
    // After a beat, prompt the next pending if any
    setTimeout(promptPendingApplies, 300);
  }}
  document.getElementById("apply-confirm-yes").onclick = function() {{ _finish("applied"); }};
  document.getElementById("apply-confirm-no").onclick = function() {{ _finish("skipped"); }};
  document.getElementById("apply-confirm-later").onclick = function() {{
    // Keep in pending. Move to back of queue so other pending get asked first.
    const arr = _readPendingApplies();
    const idx = arr.findIndex(p => p.fp === job.fp);
    if (idx >= 0) {{ const e = arr.splice(idx, 1)[0]; arr.push(e); _writePendingApplies(arr); }}
    overlay.remove();
  }};
}}

async function cycleStatus(fp, btn) {{
  const cur = getTracker()[fp]?.status || '';
  const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(cur) + 1) % STATUS_CYCLE.length];
  // Capture job meta from the card so the tracker knows what this job is
  const card = btn.closest('.card');
  const jobMeta = card ? {{
    title: (card.querySelector('.title a')?.textContent || '').trim(),
    company: (card.querySelector('.company')?.textContent || '').trim(),
    url: card.querySelector('.title a')?.href || '',
  }} : null;

  if (next === '') {{
    const r = await _trackerAction('clearStatus', {{ fp }});
    if (!r) return;
    delete _trackerCache[fp];
  }} else {{
    const r = await _trackerAction('setStatus', {{ fp, status: next, jobMeta }});
    if (!r) return;
    _trackerCache[fp] = r.record;
  }}
  refreshTrackerUI();
  filter();
  if (typeof refreshDailyGoalWidget === "function") refreshDailyGoalWidget();
}}

function _daysSince(iso) {{
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}}

function refreshTrackerUI() {{
  const tracker = getTracker();
  document.querySelectorAll('.card').forEach(card => {{
    const fp = card.dataset.fp;
    const rec = tracker[fp] || null;
    const st = rec?.status || '';
    card.dataset.status = st;
    const btn = card.querySelector('.btn.track');
    if (btn) {{
      btn.className = 'btn track ' + st;
      let label = STATUS_LABEL[st];
      if (rec && rec.lastUpdated && st) {{
        const d = _daysSince(rec.lastUpdated);
        if (d !== null) label += ' · ' + (d === 0 ? 'today' : d + 'd');
      }}
      btn.textContent = label;
    }}
    // Add/refresh Details button (only visible when tracked)
    let detailsBtn = card.querySelector('.btn.details-btn');
    if (st) {{
      if (!detailsBtn) {{
        detailsBtn = document.createElement('button');
        detailsBtn.className = 'btn details-btn';
        detailsBtn.textContent = 'Details';
        detailsBtn.style.cssText = 'background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;';
        detailsBtn.onclick = (e) => {{ e.stopPropagation(); openAppDetail(fp); }};
        const actions = card.querySelector('.actions');
        if (actions) actions.insertBefore(detailsBtn, actions.querySelector('.ghost-btn'));
      }}
    }} else if (detailsBtn) {{
      detailsBtn.remove();
    }}
    // Update badges
    const badges = card.querySelector('[data-badges]');
    if (badges) {{
      badges.querySelectorAll('.b.tracker, .b.stale').forEach(b => b.remove());
      if (st) {{
        const span = document.createElement('span');
        span.className = 'b tracker ' + st;
        span.textContent = STATUS_LABEL[st];
        badges.appendChild(document.createTextNode(' '));
        badges.appendChild(span);
        // Stale alert if no movement in 7+ days while still in active stages
        const days = rec && rec.lastUpdated ? _daysSince(rec.lastUpdated) : null;
        if (days !== null && days >= 7 && ['applied','phonescreen','onsite'].includes(st)) {{
          const stale = document.createElement('span');
          stale.className = 'b stale';
          stale.style.cssText = 'background:#fff4cc; color:#7a5300; cursor:pointer;';
          stale.textContent = 'Follow up? ' + days + 'd';
          stale.onclick = (e) => {{ e.stopPropagation(); openFollowupDraft(fp); }};
          badges.appendChild(document.createTextNode(' '));
          badges.appendChild(stale);
        }}
      }}
    }}
  }});
  updateTrackerStats();
}}

function updateTrackerStats() {{
  const t = getTracker();
  const counts = {{ applied: 0, phonescreen: 0, onsite: 0, offer: 0, rejected: 0 }};
  Object.values(t).forEach(v => {{ if (counts[v.status] !== undefined) counts[v.status]++; }});
  for (const k of Object.keys(counts)) {{
    const el = document.getElementById('cnt-' + k);
    if (el) el.textContent = counts[k];
  }}
  const totalApplied = counts.applied + counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const responses = counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const respEl = document.getElementById('cnt-response');
  if (respEl) respEl.textContent = totalApplied === 0 ? '--' : Math.round(100 * responses / totalApplied) + '%';
  // Render funnel
  renderFunnel(counts);
}}

function renderFunnel(counts) {{
  const el = document.getElementById('funnel-row');
  if (!el) return;
  // The funnel respects status progression. "Total Applied" = anyone who ever applied
  // (includes those who progressed beyond), so we use cumulative counts.
  const c_applied = counts.applied + counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const c_phone = counts.phonescreen + counts.onsite + counts.offer; // people who reached at least phone screen
  const c_onsite = counts.onsite + counts.offer;
  const c_offer = counts.offer;
  function stage(label, count, prevCount, color) {{
    const pct = prevCount > 0 ? Math.round(100 * count / prevCount) + '%' : '';
    return '<div class="funnel-stage" style="flex:1; background:' + color + '; padding:10px 14px; border-radius:8px; color:#5C5CD6; min-width:0;">' +
      '<div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#666; font-weight:600;">' + label + '</div>' +
      '<div style="font-size:22px; font-weight:700; line-height:1.1; margin-top:2px;">' + count + '</div>' +
      (pct ? '<div style="font-size:11px; color:#666; margin-top:2px;">' + pct + ' from prev</div>' : '<div style="font-size:11px; color:#999; margin-top:2px;">&nbsp;</div>') +
    '</div>';
  }}
  el.innerHTML =
    stage('Applied', c_applied, 0, '#e9efff') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Phone Screen', c_phone, c_applied, '#fff4e0') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Onsite', c_onsite, c_phone, '#f0e6ff') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Offer', c_offer, c_onsite, '#e6fff0') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Rejected', counts.rejected, c_applied, '#ffe6e6');
}}

// ====================================================================
// Application detail side panel
// ====================================================================
let _currentDetailFp = null;

async function openAppDetail(fp) {{
  _currentDetailFp = fp;
  const rec = getTracker()[fp];
  if (!rec) {{ alert('Not in tracker'); return; }}
  document.getElementById('app-detail-title').textContent = (rec.title || 'Application') + ' @ ' + (rec.company || '');
  document.getElementById('app-detail-body').innerHTML = _renderAppDetail(rec);
  document.getElementById('app-detail-modal').classList.add('show');
}}

function closeAppDetail() {{
  document.getElementById('app-detail-modal').classList.remove('show');
  _currentDetailFp = null;
}}

function _renderAppDetail(rec) {{
  const days = _daysSince(rec.lastUpdated);
  const daysTxt = days === null ? '' : (days === 0 ? 'today' : days + ' days ago');
  let html = '';
  html += '<div style="background:#f8f9fb; border:1px solid #e6e8eb; border-radius:8px; padding:12px 14px; margin-bottom:14px;">';
  html += '<div style="font-size:13px;"><strong>Status:</strong> ' + (rec.status || 'untouched') + ' · last update ' + daysTxt + '</div>';
  // Status history
  if (rec.statusHistory && rec.statusHistory.length) {{
    html += '<div style="font-size:12px; color:#666; margin-top:6px;">Timeline: ';
    html += rec.statusHistory.map(h => h.status + ' (' + new Date(h.at).toLocaleDateString() + ')').join(' → ');
    html += '</div>';
  }}
  html += '</div>';
  // Recruiter
  html += '<div class="prep-section"><div class="prep-label">Recruiter / contact</div>';
  html += '<input type="text" id="detail-recruiter" value="' + _esc(rec.recruiter || '') + '" placeholder="name@example.com or LinkedIn URL" style="width:100%; box-sizing:border-box; padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px; font-size:13px;" />';
  html += '<button class="btn primary" style="margin-top:8px;" onclick="saveAppRecruiter()">Save</button>';
  html += '<span id="detail-recruiter-status" style="font-size:12px; color:#555; margin-left:10px;"></span></div>';
  // Notes
  html += '<div class="prep-section"><div class="prep-label">Notes</div>';
  html += '<textarea id="detail-notes" rows="6" placeholder="Hiring manager name, what they said, what to follow up on…" style="width:100%; box-sizing:border-box; padding:10px; font-size:13px; border:1px solid #ccd0d6; border-radius:6px; resize:vertical;">' + _esc(rec.notes || '') + '</textarea>';
  html += '<button class="btn primary" style="margin-top:8px;" onclick="saveAppNotes()">Save notes</button>';
  html += '<span id="detail-notes-status" style="font-size:12px; color:#555; margin-left:10px;"></span></div>';
  // Salary (if offer)
  if (rec.status === 'offer' || rec.salary) {{
    const s = rec.salary || {{}};
    html += '<div class="prep-section"><div class="prep-label">Offer details</div>';
    html += '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">';
    html += '<input id="sal-base" type="text" placeholder="Base salary" value="' + _esc(s.base || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '<input id="sal-bonus" type="text" placeholder="Bonus %" value="' + _esc(s.bonus || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '<input id="sal-equity" type="text" placeholder="Equity (vesting)" value="' + _esc(s.equity || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '<input id="sal-signing" type="text" placeholder="Signing bonus" value="' + _esc(s.signing || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '</div>';
    html += '<button class="btn primary" style="margin-top:8px;" onclick="saveAppSalary()">Save compensation</button>';
    html += '<span id="detail-salary-status" style="font-size:12px; color:#555; margin-left:10px;"></span></div>';
  }}
  // Saved Prep kit
  if (rec.prepKit) {{
    html += '<div class="prep-section"><div class="prep-label">Saved Prep kit</div>';
    if (rec.prepKit.summary) html += '<div style="font-size:13px; padding:10px; background:#fafbfc; border-radius:6px; margin-bottom:8px; white-space:pre-wrap;">' + _esc(rec.prepKit.summary) + '</div>';
    html += '<button class="btn primary" onclick="reopenPrepFromTracker()">View full prep kit</button></div>';
  }}
  // Actions
  html += '<div class="prep-section">';
  html += '<button class="btn primary" onclick="openFollowupDraft(\\''+rec.fp+'\\')">Draft follow-up email</button> ';
  html += '<button class="btn primary" onclick="openInterviewPrep(\\''+rec.fp+'\\')">Generate interview prep</button> ';
  if (rec.interviewPrep && rec.interviewPrep.length) {{
    html += '<button class="btn primary" onclick="showSavedInterviewPrep()">View saved Q&amp;A (' + rec.interviewPrep.length + ')</button>';
  }}
  html += '</div>';
  return html;
}}

async function saveAppNotes() {{
  const notes = document.getElementById('detail-notes').value;
  const status = document.getElementById('detail-notes-status');
  status.textContent = 'Saving…';
  const r = await _trackerAction('setNotes', {{ fp: _currentDetailFp, notes }});
  if (r) {{
    _trackerCache[_currentDetailFp] = r.record;
    status.style.color = '#0a6b3a';
    status.textContent = 'Saved.';
  }}
}}

async function saveAppRecruiter() {{
  const recruiter = document.getElementById('detail-recruiter').value;
  const status = document.getElementById('detail-recruiter-status');
  status.textContent = 'Saving…';
  const r = await _trackerAction('setRecruiter', {{ fp: _currentDetailFp, recruiter }});
  if (r) {{
    _trackerCache[_currentDetailFp] = r.record;
    status.style.color = '#0a6b3a';
    status.textContent = 'Saved.';
  }}
}}

async function saveAppSalary() {{
  const salary = {{
    base: document.getElementById('sal-base').value,
    bonus: document.getElementById('sal-bonus').value,
    equity: document.getElementById('sal-equity').value,
    signing: document.getElementById('sal-signing').value,
  }};
  const status = document.getElementById('detail-salary-status');
  status.textContent = 'Saving…';
  const r = await _trackerAction('saveSalary', {{ fp: _currentDetailFp, salary }});
  if (r) {{
    _trackerCache[_currentDetailFp] = r.record;
    status.style.color = '#0a6b3a';
    status.textContent = 'Saved.';
  }}
}}

function reopenPrepFromTracker() {{
  const rec = getTracker()[_currentDetailFp];
  if (!rec || !rec.prepKit) return;
  closeAppDetail();
  document.getElementById('prep-modal-title').textContent = 'Materials for ' + rec.title + ' @ ' + rec.company;
  document.getElementById('prep-status').style.display = 'none';
  document.getElementById('prep-output').style.display = 'block';
  document.getElementById('prep-summary').textContent = rec.prepKit.summary || '(no summary)';
  document.getElementById('prep-cover').textContent = rec.prepKit.coverLetter || '(no cover letter)';
  document.getElementById('prep-linkedin').textContent = rec.prepKit.linkedin || '(no LinkedIn intro)';
  _tailoredResume = rec.prepKit.tailoredResume || null;
  _tailoredJobMeta = {{ jobTitle: rec.title, company: rec.company }};
  const sec = document.getElementById('prep-resume-section');
  if (_tailoredResume && _tailoredResume.personal) {{
    document.getElementById('prep-resume-preview').innerHTML = _renderResumeHTML(_tailoredResume);
    sec.style.display = 'block';
  }} else {{
    sec.style.display = 'none';
  }}
  document.getElementById('prep-modal').classList.add('show');
}}

// ====================================================================
// Follow-up email drafter
// ====================================================================
let _currentFollowup = null;
async function openFollowupDraft(fp) {{
  document.getElementById('followup-modal').classList.add('show');
  document.getElementById('followup-status').style.display = 'block';
  document.getElementById('followup-status').textContent = 'Generating with Claude…';
  document.getElementById('followup-output').style.display = 'none';
  const editKey = getEditKey(); // not actually needed; followup is public — but include for consistency
  try {{
    const r = await fetch(FOLLOWUP_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ fp }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      document.getElementById('followup-status').textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      return;
    }}
    _currentFollowup = data;
    const rec = getTracker()[fp];
    _currentFollowup.to = (rec && rec.recruiter) || '';
    document.getElementById('followup-subject').textContent = data.subject || '';
    document.getElementById('followup-body').textContent = data.body || '';
    document.getElementById('followup-status').style.display = 'none';
    document.getElementById('followup-output').style.display = 'block';
  }} catch (e) {{
    document.getElementById('followup-status').textContent = 'Failed: ' + (e.message || e);
  }}
}}
function closeFollowupModal() {{ document.getElementById('followup-modal').classList.remove('show'); }}
function copyFollowupBody(btn) {{
  if (!_currentFollowup) return;
  const txt = (_currentFollowup.subject || '') + '\\n\\n' + (_currentFollowup.body || '');
  navigator.clipboard.writeText(txt).then(() => {{ btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Copy', 1500); }});
}}
function openFollowupMailto() {{
  if (!_currentFollowup) return;
  const to = _currentFollowup.to || '';
  const m = 'mailto:' + encodeURIComponent(to) + '?subject=' + encodeURIComponent(_currentFollowup.subject || '') + '&body=' + encodeURIComponent(_currentFollowup.body || '');
  window.location.href = m;
}}

// ====================================================================
// Interview prep
// ====================================================================
async function openInterviewPrep(fp) {{
  const rec = getTracker()[fp];
  if (!rec) return;
  document.getElementById('interview-modal').classList.add('show');
  document.getElementById('interview-title').textContent = 'Interview prep — ' + rec.title + ' @ ' + rec.company;
  document.getElementById('interview-status').style.display = 'block';
  document.getElementById('interview-status').textContent = 'Generating with Claude… this takes 20-30 seconds.';
  document.getElementById('interview-output').style.display = 'none';
  try {{
    const r = await fetch(INTERVIEW_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ jobTitle: rec.title, company: rec.company }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      document.getElementById('interview-status').textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      return;
    }}
    document.getElementById('interview-status').style.display = 'none';
    document.getElementById('interview-output').style.display = 'block';
    document.getElementById('interview-output').innerHTML = _renderInterviewPrep(data.questions || []);
    // Save to tracker
    const ed = getEditKey();
    if (ed) {{
      await _trackerAction('saveInterviewPrep', {{ fp, interviewPrep: data.questions || [] }});
      const got = getTracker()[fp];
      if (got) got.interviewPrep = data.questions || [];
    }}
  }} catch (e) {{
    document.getElementById('interview-status').textContent = 'Failed: ' + (e.message || e);
  }}
}}
function closeInterviewModal() {{ document.getElementById('interview-modal').classList.remove('show'); }}
function _renderInterviewPrep(qs) {{
  if (!qs || !qs.length) return '<p>No questions generated.</p>';
  return qs.map((q, i) => {{
    const type = q.type || '';
    return '<div class="prep-section">' +
      '<div class="prep-label">' + (i+1) + '. ' + _esc(q.q || '') + (type ? ' <span style="background:#eef; color:#5C5CD6; padding:1px 7px; border-radius:10px; font-size:10px; margin-left:6px;">' + type + '</span>' : '') + '</div>' +
      '<pre class="prep-text">' + _esc(q.a || '') + '</pre>' +
      '</div>';
  }}).join('');
}}
function showSavedInterviewPrep() {{
  const rec = getTracker()[_currentDetailFp];
  if (!rec || !rec.interviewPrep) return;
  document.getElementById('interview-modal').classList.add('show');
  document.getElementById('interview-title').textContent = 'Interview prep — ' + rec.title + ' @ ' + rec.company;
  document.getElementById('interview-status').style.display = 'none';
  document.getElementById('interview-output').style.display = 'block';
  document.getElementById('interview-output').innerHTML = _renderInterviewPrep(rec.interviewPrep);
}}

// --- View mode toggle ---------------------------------------------------
let viewMode = localStorage.getItem('htj_view') || 'all';

function setView(mode) {{
  viewMode = mode;
  localStorage.setItem('htj_view', mode);
  document.body.classList.toggle('apps-mode', mode === 'apps');
  const allBtn = document.getElementById('view-all');
  const appsBtn = document.getElementById('view-apps');
  if (allBtn) allBtn.classList.toggle('active', mode === 'all');
  if (appsBtn) appsBtn.classList.toggle('active', mode === 'apps');
  filter();
}}

// --- Sorting ------------------------------------------------------------
function sortCards() {{
  const sel = document.getElementById('sortBy');
  if (!sel) return;
  const by = sel.value || 'score';
  const grid = document.getElementById('grid');
  const cards = Array.from(grid.querySelectorAll('.card'));
  function _secondary(a, b) {{
    if (by === 'salary') return (parseInt(b.dataset.salaryMax || '0', 10)) - (parseInt(a.dataset.salaryMax || '0', 10));
    if (by === 'recent') return (b.dataset.lastSeen || '').localeCompare(a.dataset.lastSeen || '');
    if (by === 'ghost') return (b.dataset.firstSeen || '').localeCompare(a.dataset.firstSeen || '');
    return (parseInt(b.dataset.score || '0', 10)) - (parseInt(a.dataset.score || '0', 10));
  }}
  cards.sort((a, b) => {{
    // PRIMARY criterion: any LinkedIn connection at a company that's
    // hiring in the user's industry wins, regardless of whether the
    // contact is a recruiter or a peer. Industry match is already
    // enforced upstream (jobs without it never reach this list).
    const aHas = a.querySelector('.contact-badge') ? 1 : 0;
    const bHas = b.querySelector('.contact-badge') ? 1 : 0;
    if (aHas !== bHas) return bHas - aHas;
    return _secondary(a, b);
  }});
  cards.forEach(c => grid.appendChild(c));
  // Update the "X jobs with contacts" indicator if it exists
  const ind = document.getElementById('contacts-priority-indicator');
  if (ind) {{
    const withContacts = cards.filter(c => c.querySelector('.contact-badge') && c.style.display !== 'none').length;
    const withHiring = cards.filter(c => {{
      const b = c.querySelector('.contact-badge');
      return b && b.classList.contains('hiring') && c.style.display !== 'none';
    }}).length;
    if (withContacts > 0) {{
      ind.style.display = '';
      // Single tier — any connection at the hiring company. Recruiter count
      // is shown as supplementary info in the same line.
      const recruiterNote = withHiring > 0 ? ' <span style="color:#b85c00;">(' + withHiring + ' include a recruiter/HR contact \ud83c\udfaf)</span>' : '';
      ind.innerHTML = '<span style="font-size:11px;font-weight:600;color:#0a66c2;">\ud83e\udd1d ' + withContacts + ' job' + (withContacts === 1 ? '' : 's') + ' at companies where you have a LinkedIn connection \u2014 shown first' + recruiterNote + '</span>';
    }} else {{
      ind.style.display = 'none';
      ind.innerHTML = '';
    }}
  }}
}}

// --- Filtering ----------------------------------------------------------
function setWindow(btn, w) {{
  activeWindow = String(w);
  try {{ localStorage.setItem(RECENCY_WINDOW_KEY, String(w)); }} catch (e) {{}}
  try {{ pushPrefToProfile("recencyWindow", String(w)); }} catch (e) {{}}
  // Only toggle time-window pills (don't touch View / Type pills)
  document.querySelectorAll('[data-window]').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');
  filter();
}}
// On load, restore the saved recency window
function _restoreRecencyWindow() {{
  try {{
    const w = activeWindow;
    document.querySelectorAll('[data-window]').forEach(p => {{
      p.classList.toggle('active', p.getAttribute('data-window') === String(w));
    }});
    filter();
  }} catch (e) {{}}
}}

// --- Employment-type filter --------------------------------------------
let employmentFilter = localStorage.getItem('htj_employment') || 'all';

function setEmploymentFilter(mode) {{
  employmentFilter = mode;
  localStorage.setItem('htj_employment', mode);
  ['all','full-time','contract'].forEach(k => {{
    const el = document.getElementById('type-' + (k === 'full-time' ? 'fulltime' : k));
    if (el) el.classList.toggle('active', k === mode);
  }});
  filter();
}}
function filter() {{
  const q = document.getElementById('q').value.toLowerCase();
  const flt = document.getElementById('srOnly').value;
  const trk = document.getElementById('trackedFilter').value;
  const sal = document.getElementById('salaryFilter')?.value || '';
  const rec = document.getElementById('recruiterFilter')?.value || 'hide';
  const tracker = getTracker();
  const cards = Array.from(document.querySelectorAll('.card'));
  let shown = 0;
  cards.forEach(c => {{
    const text = c.innerText.toLowerCase();
    const senior = c.dataset.senior === '1';
    const remote = c.dataset.remote === '1';
    const days = parseInt(c.dataset.listedDays || '9999', 10);
    const salaryMax = parseInt(c.dataset.salaryMax || '0', 10);
    const st = tracker[c.dataset.fp]?.status || '';
    let show = text.includes(q);
    if (viewMode === 'apps' && !st) show = false;
    if (flt === 'srOnly' && !(senior && remote)) show = false;
    if (flt === 'sOnly' && !senior) show = false;
    if (flt === 'rOnly' && !remote) show = false;
    if (activeWindow !== 'all') {{
      const maxDays = parseInt(activeWindow, 10);
      if (days > maxDays) show = false;
    }}
    if (trk === 'untouched' && st) show = false;
    else if (trk && trk !== 'untouched' && st !== trk) show = false;
    if (sal === 'listed' && salaryMax === 0) show = false;
    else if (sal && sal !== 'listed' && salaryMax < parseInt(sal, 10)) show = false;
    // Employment-type filter — unknown counts as full-time
    const emp = c.dataset.employment || 'unknown';
    if (employmentFilter === 'contract' && emp !== 'contract') show = false;
    else if (employmentFilter === 'full-time' && emp === 'contract') show = false;
    const isRecr = c.dataset.recruiter === '1';
    if (rec === 'hide' && isRecr) show = false;
    else if (rec === 'only' && !isRecr) show = false;
    c.style.display = show ? '' : 'none';
    if (show) shown++;
  }});
  const counter = document.getElementById('shown-counter');
  if (counter) counter.textContent = shown;
}}

// --- Resume editor (Cloudflare Worker + KV) -----------------------------
// (WORKER_BASE, USER_SLUG, USER_QS now declared earlier near the tracker URLs)
const RESUME_WORKER_URL = WORKER_BASE + '/resume' + USER_QS;
const VERSIONS_WORKER_URL = WORKER_BASE + '/resume-versions' + USER_QS;
const PARSE_RESUME_WORKER_URL = WORKER_BASE + '/parse-resume' + USER_QS;

// pdf.js worker path (must be set once before parsing PDFs)
if (window.pdfjsLib) {{
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}}

let _pendingUploadFile = null;

// --- Cross-device preference sync ---------------------------------------
// dailyTarget / recencyWindow / defaultSort live in localStorage for fast UI
// access, but we also mirror them to skills_profile via patchFields so the
// user's choices follow them between Chrome / Safari / mobile.
//
// On boot we GET /skills-profile and, if any of these fields are present on
// the server, copy them down into localStorage (server wins on tie). Then
// every time the user changes one, we POST patchFields to push it up.
async function hydratePrefsFromProfile() {{
  try {{
    const r = await fetch(WORKER_BASE + "/skills-profile" + USER_QS);
    if (!r.ok) return;
    const data = await r.json().catch(function() {{ return {{}}; }});
    const profile = (data && data.profile) || {{}};
    let touched = false;
    if (profile && profile.dailyTarget != null) {{
      const n = parseInt(profile.dailyTarget, 10);
      if (!isNaN(n) && n > 0 && n < 100) {{
        try {{ localStorage.setItem(DAILY_TARGET_KEY, String(n)); touched = true; }} catch (e) {{}}
      }}
    }}
    if (profile && typeof profile.recencyWindow === 'string' && profile.recencyWindow) {{
      try {{
        localStorage.setItem(RECENCY_WINDOW_KEY, profile.recencyWindow);
        activeWindow = String(profile.recencyWindow);
        touched = true;
      }} catch (e) {{}}
    }}
    if (touched) {{
      try {{ _restoreRecencyWindow(); }} catch (e) {{}}
      try {{ refreshDailyGoalWidget(); }} catch (e) {{}}
    }}
    // F4: apply salaryFloor / hideNoSalary from profile to the dropdown
    try {{ applySalaryPrefFromProfile(profile); }} catch (e) {{}}
  }} catch (e) {{ /* non-fatal: localStorage still works */ }}
}}

// Push a single scalar pref up to the user's skills_profile. Best-effort:
// silently swallow auth/network errors so the local UX is never blocked.
async function pushPrefToProfile(field, value) {{
  try {{
    const editKey = (typeof getEditKey === "function")
      ? localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key")
      : null;
    if (!editKey) return;  // not logged in yet; localStorage still works
    const patch = {{}}; patch[field] = value;
    await fetch(WORKER_BASE + "/skills-profile" + USER_QS, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
      body: JSON.stringify({{ patchFields: patch }})
    }});
  }} catch (e) {{ /* non-fatal */ }}
}}

// ==============================================================
// F1: Not-for-me dismiss + pattern learning
// ==============================================================
const DISMISSED_KEY = 'htj_dismissed_' + USER_SLUG;
const DISMISSED_SIG_KEY = 'htj_dismissed_signals_' + USER_SLUG;

function _loadDismissedSet() {{
  try {{ return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]')); }}
  catch (e) {{ return new Set(); }}
}}
function _saveDismissedSet(set) {{
  try {{ localStorage.setItem(DISMISSED_KEY, JSON.stringify(Array.from(set).slice(-500))); }} catch (e) {{}}
}}
function _loadDismissedSignals() {{
  try {{ return JSON.parse(localStorage.getItem(DISMISSED_SIG_KEY) || '[]'); }}
  catch (e) {{ return []; }}
}}
function _saveDismissedSignals(arr) {{
  try {{ localStorage.setItem(DISMISSED_SIG_KEY, JSON.stringify(arr.slice(-200))); }} catch (e) {{}}
}}

function dismissJob(fp, btn) {{
  const card = btn && btn.closest('.card');
  if (!card) return;
  const set = _loadDismissedSet();
  set.add(fp);
  _saveDismissedSet(set);
  const signals = _loadDismissedSignals();
  signals.push({{
    fp: fp,
    title: card.querySelector('.title') ? card.querySelector('.title').innerText.trim() : '',
    company: card.querySelector('.company') ? card.querySelector('.company').innerText.trim() : '',
    norm: card.getAttribute('data-title-norm') || '',
    ts: Date.now()
  }});
  _saveDismissedSignals(signals);
  card.style.transition = 'opacity 200ms';
  card.style.opacity = '0';
  setTimeout(function() {{ card.style.display = 'none'; }}, 220);
  // After every 5 dismissals, scan for patterns the user keeps rejecting.
  if (signals.length > 0 && signals.length % 5 === 0) {{
    setTimeout(_suggestBlocklistFromDismissals, 600);
  }}
}}

function _suggestBlocklistFromDismissals() {{
  const signals = _loadDismissedSignals();
  // Count first-2-word title prefix occurrences
  const counts = {{}};
  signals.forEach(function(s) {{
    const t = (s.title || '').toLowerCase().split(/[\s,\-]+/).filter(Boolean);
    if (t.length < 2) return;
    const key = t.slice(0, 2).join(' ');
    counts[key] = (counts[key] || 0) + 1;
  }});
  // Find prefix with >=3 hits that isn't already in negativeTitles
  const candidates = Object.entries(counts).filter(function(kv) {{ return kv[1] >= 3; }})
    .sort(function(a, b) {{ return b[1] - a[1]; }});
  if (!candidates.length) return;
  const [phrase, count] = candidates[0];
  if (sessionStorage.getItem('htj_dismissed_offer_' + phrase)) return;
  sessionStorage.setItem('htj_dismissed_offer_' + phrase, '1');
  // Build the banner via DOM API to avoid quote-escaping issues
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;bottom:18px;right:18px;background:#fffbe6;border:1px solid #f0c14b;border-radius:8px;padding:14px 16px;max-width:340px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.18);font-size:13px;';
  const head = document.createElement('div');
  head.innerHTML = '<strong>Pattern detected</strong>';
  banner.appendChild(head);
  const txt = document.createElement('div');
  txt.style.margin = '6px 0 12px 0';
  txt.textContent = 'You have dismissed ' + count + ' jobs whose title starts with "' + phrase + '". Hide these permanently?';
  banner.appendChild(txt);
  const yes = document.createElement('button');
  yes.className = 'btn primary';
  yes.style.marginRight = '8px';
  yes.textContent = 'Yes, hide these';
  yes.addEventListener('click', function() {{ _acceptBlocklist(phrase, yes); }});
  banner.appendChild(yes);
  const no = document.createElement('button');
  no.className = 'btn ghost-btn';
  no.textContent = 'No thanks';
  no.addEventListener('click', function() {{ banner.remove(); }});
  banner.appendChild(no);
  document.body.appendChild(banner);
}}

async function _acceptBlocklist(phrase, btn) {{
  // Append to user profile.negativeTitles and push via patchFields
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS);
    const data = await r.json().catch(function() {{ return {{}}; }});
    const cur = ((data && data.profile && data.profile.negativeTitles) || []).slice();
    if (!cur.includes(phrase)) cur.push(phrase);
    await pushPrefToProfile('negativeTitles', cur);
    if (btn && btn.parentElement) btn.parentElement.innerHTML = '<em style="color:#0a6b3a;">Saved. \"' + phrase + '\" will be hidden after the next refresh.</em>';
  }} catch (e) {{ alert('Could not save \u2014 try again.'); }}
}}

function _hideDismissedCards() {{
  const set = _loadDismissedSet();
  if (!set.size) return;
  document.querySelectorAll('.card[data-fp]').forEach(function(c) {{
    if (set.has(c.getAttribute('data-fp'))) c.style.display = 'none';
  }});
}}

// ==============================================================
// F5: Why-was-this-shown tooltip + cross-company cluster badge
// ==============================================================
function showWhyMatched(fp, btn) {{
  const card = btn && btn.closest('.card');
  if (!card) return;
  const why = card.getAttribute('data-why') || 'No explanation available.';
  // Toggle existing
  const existing = card.querySelector('.why-tooltip');
  if (existing) {{ existing.remove(); return; }}
  const tip = document.createElement('div');
  tip.className = 'why-tooltip';
  tip.style.cssText = 'margin-top:8px;padding:8px 10px;background:#f4f6fb;border-left:3px solid #5C5CD6;border-radius:4px;font-size:12px;color:#444;line-height:1.5;';
  tip.textContent = 'Matched because: ' + why;
  card.appendChild(tip);
}}

function _renderClusterBadges() {{
  document.querySelectorAll('.card[data-cluster-count]').forEach(function(c) {{
    const n = parseInt(c.getAttribute('data-cluster-count') || '0', 10);
    if (n < 1) return;
    const names = c.getAttribute('data-cluster-companies') || '';
    if (c.querySelector('.cluster-badge')) return;  // already rendered
    const badgesRow = c.querySelector('[data-badges]');
    if (!badgesRow) return;
    const b = document.createElement('span');
    b.className = 'b cluster-badge';
    b.style.cssText = 'background:#eef2ff;color:#3b3f8a;border:1px solid #c7d2fe;';
    b.title = 'Also hiring this role: ' + names;
    b.textContent = 'Also at ' + n + ' other employer' + (n === 1 ? '' : 's');
    badgesRow.appendChild(document.createTextNode(' '));
    badgesRow.appendChild(b);
  }});
}}

// ==============================================================
// F4: Apply salaryFloor / hideNoSalary from profile into the existing
// salary dropdown so jobs the user explicitly excluded are not shown.
// ==============================================================
function applySalaryPrefFromProfile(profile) {{
  // Intentionally a no-op now: auto-applying salaryFloor was hiding most jobs
  // (most ATS listings have no listed salary, so the gate filtered to 0).
  // Users opt in by selecting the salary dropdown themselves; their choice
  // still syncs to profile.salaryFloor via the change handler.
  return;
}}

// Save salary choice back to profile so it syncs across devices.
(function _hookSalarySync() {{
  function run() {{
    const sel = document.getElementById('salaryFilter');
    if (!sel) return;
    sel.addEventListener('change', function() {{
      const v = sel.value;
      if (v === 'listed') {{
        pushPrefToProfile('hideNoSalary', true);
        pushPrefToProfile('salaryFloor', 0);
      }} else if (v && /^\d+$/.test(v)) {{
        pushPrefToProfile('hideNoSalary', false);
        pushPrefToProfile('salaryFloor', parseInt(v, 10));
      }} else {{
        pushPrefToProfile('hideNoSalary', false);
        pushPrefToProfile('salaryFloor', 0);
      }}
    }});
  }}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
}})();

// ==============================================================
// F2: AI re-rank the visible cards (Claude Haiku via Worker /rerank-titles)
// ==============================================================
const RERANK_CACHE_KEY = 'htj_ai_rerank_' + USER_SLUG;
const RERANK_TTL_MS = 24 * 60 * 60 * 1000;

function _loadRerankCache() {{
  try {{
    const raw = JSON.parse(localStorage.getItem(RERANK_CACHE_KEY) || '{{}}');
    const now = Date.now();
    const out = {{}};
    for (const [fp, v] of Object.entries(raw)) {{
      if (v && v.ts && (now - v.ts) < RERANK_TTL_MS) out[fp] = v;
    }}
    return out;
  }} catch (e) {{ return {{}}; }}
}}
function _saveRerankCache(cache) {{
  try {{ localStorage.setItem(RERANK_CACHE_KEY, JSON.stringify(cache)); }} catch (e) {{}}
}}

async function aiRerankCards() {{
  // Disabled if user explicitly turned it off
  if (localStorage.getItem('htj_ai_rerank_off_' + USER_SLUG) === '1') return;
  const cards = Array.from(document.querySelectorAll('.card[data-fp]'));
  if (!cards.length) return;
  const cache = _loadRerankCache();
  const need = [];
  cards.forEach(function(c) {{
    if (c.style.display === 'none') return;
    const fp = c.getAttribute('data-fp');
    if (!fp) return;
    if (cache[fp]) {{ _applyAiScore(c, cache[fp].score); return; }}
    const titleEl = c.querySelector('.title a, .title');
    const title = titleEl ? titleEl.innerText.trim() : '';
    if (title) need.push({{fp: fp, title: title}});
  }});
  if (cache && Object.keys(cache).length) {{ _resortByAiScore(); }}
  if (!need.length) return;
  // Batch in chunks of 40 to keep prompt size sane
  const batches = [];
  for (let i = 0; i < need.length; i += 40) batches.push(need.slice(i, i + 40));
  for (const batch of batches) {{
    try {{
      const r = await fetch(WORKER_BASE + '/rerank-titles' + USER_QS, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{items: batch}})
      }});
      if (!r.ok) continue;
      const data = await r.json().catch(function() {{ return {{}}; }});
      const scores = (data && data.scores) || {{}};
      for (const [fp, score] of Object.entries(scores)) {{
        cache[fp] = {{score: score, ts: Date.now()}};
        const c = document.querySelector('.card[data-fp="' + fp + '"]');
        if (c) _applyAiScore(c, score);
      }}
      _saveRerankCache(cache);
      _resortByAiScore();
    }} catch (e) {{ /* network blip, skip batch */ }}
  }}
}}

function _applyAiScore(card, score) {{
  const scoreEl = card.querySelector('.score');
  if (!scoreEl) return;
  card.setAttribute('data-ai-score', String(score));
  scoreEl.textContent = String(score);
  scoreEl.title = 'AI fit score (' + score + '/100)';
}}

function _resortByAiScore() {{
  const grid = document.getElementById('grid');
  if (!grid) return;
  const cards = Array.from(grid.querySelectorAll('.card[data-fp]'));
  cards.sort(function(a, b) {{
    const sa = parseInt(a.getAttribute('data-ai-score') || a.getAttribute('data-score') || '0', 10);
    const sb = parseInt(b.getAttribute('data-ai-score') || b.getAttribute('data-score') || '0', 10);
    return sb - sa;
  }});
  cards.forEach(function(c) {{ grid.appendChild(c); }});
}}

// On first visit via invite link, the password is in the URL as ?key=XXX.
// Capture it, store to localStorage, then strip from URL so it isn't visible later.
(function bootstrapDailyWidget() {{
  function run() {{
    try {{ refreshDailyGoalWidget(); }} catch (e) {{}}
    try {{ promptPendingApplies(); }} catch (e) {{}}
    try {{ _restoreRecencyWindow(); }} catch (e) {{}}
    // Pull cross-device prefs from the server; happens async, will re-render
    // the widget + recency pills once it lands.
    try {{ hydratePrefsFromProfile(); }} catch (e) {{}}
    // F1: hide jobs the user has already dismissed in this browser.
    try {{ _hideDismissedCards(); }} catch (e) {{}}
    // F5: render cross-company "Also at" badges.
    try {{ _renderClusterBadges(); }} catch (e) {{}}
    // F2: AI re-rank the visible cards in the background.
    try {{ aiRerankCards(); }} catch (e) {{}}
  }}
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
}})();

(function captureInviteKey() {{
  try {{
    const params = new URLSearchParams(window.location.search);
    const k = params.get('key');
    if (k) {{
      // Store per-user key so each dashboard remembers its own
      localStorage.setItem('htj_resume_key_' + USER_SLUG, k);
      params.delete('key');
      const q = params.toString();
      const newUrl = window.location.pathname + (q ? '?' + q : '') + window.location.hash;
      window.history.replaceState({{}}, '', newUrl);
    }}
  }} catch (e) {{ /* non-fatal */ }}
}})();

function getEditKey() {{
  // Silent lookup only — no native prompt. Callers handle null by either
  // falling back to admin-key auth or showing the inline Verify Session modal.
  return localStorage.getItem('htj_resume_key_' + USER_SLUG)
      || localStorage.getItem('htj_resume_key')
      || null;
}}

// Inline session-verify modal — replaces the old prompt('Enter the password')
// flow. Shows up when an action needs auth but no edit key is stored. The user
// clicks Confirm; if an admin key is stored we try that, otherwise we email
// for a fresh invite.
function showVerifyModal(onConfirm) {{
  // Admin-key fallback: silently confirm if it's stored
  const adminKey = localStorage.getItem('htj_admin_key');
  if (adminKey) {{ onConfirm && onConfirm(adminKey, 'admin'); return; }}
  // Build modal with DOM API (no innerHTML, no quote-escape risk)
  let m = document.getElementById('verify-modal');
  if (m) {{ m.style.display = 'flex'; return; }}
  m = document.createElement('div');
  m.id = 'verify-modal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;z-index:99999;';
  const card = document.createElement('div');
  card.style.cssText = 'background:#fff;border-radius:12px;padding:24px;max-width:380px;width:90%;box-shadow:0 6px 24px rgba(0,0,0,0.2);font-family:Inter,sans-serif;';
  const title = document.createElement('div');
  title.style.cssText = 'font-size:16px;font-weight:700;margin-bottom:8px;';
  title.textContent = 'Confirm changes';
  card.appendChild(title);
  const desc = document.createElement('div');
  desc.style.cssText = 'font-size:13px;color:#555;margin-bottom:16px;line-height:1.5;';
  desc.textContent = 'Your save key is not stored in this browser. Click Confirm to try anyway, or email us for a fresh invite link.';
  card.appendChild(desc);
  const row = document.createElement('div');
  row.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
  const cancel = document.createElement('button');
  cancel.textContent = 'Cancel';
  cancel.style.cssText = 'padding:8px 14px;border:1px solid #d0d4dc;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;';
  cancel.onclick = function() {{ m.style.display = 'none'; }};
  const emailLink = document.createElement('a');
  emailLink.textContent = 'Email for link';
  emailLink.href = 'mailto:info@officebeatllc.com?subject=Fresh%20invite%20link%20needed';
  emailLink.style.cssText = 'padding:8px 14px;border:1px solid #d0d4dc;border-radius:6px;background:#fff;text-decoration:none;color:#333;font-size:13px;display:inline-block;';
  const confirm = document.createElement('button');
  confirm.textContent = 'Confirm';
  confirm.style.cssText = 'padding:8px 14px;border:none;border-radius:6px;background:#5C5CD6;color:#fff;cursor:pointer;font-size:13px;font-weight:600;';
  confirm.onclick = function() {{ m.style.display = 'none'; onConfirm && onConfirm(null, 'none'); }};
  row.appendChild(cancel); row.appendChild(emailLink); row.appendChild(confirm);
  card.appendChild(row);
  m.appendChild(card);
  document.body.appendChild(m);
}}

function setResumeTab(name) {{
  document.querySelectorAll('#resume-editor .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('#resume-editor .tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
  if (name === 'versions') loadVersions();
  if (name === 'profile') loadProfile();
}}

const PROFILE_WORKER_URL = WORKER_BASE + '/skills-profile' + USER_QS;

async function loadProfile() {{
  const el = document.getElementById('profile-display');
  const actions = document.getElementById('profile-actions');
  el.innerHTML = '<p style="font-size:12px;color:#888;">Loading profile…</p>';
  if (actions) actions.style.display = 'none';
  try {{
    const r = await fetch(PROFILE_WORKER_URL);
    const data = await r.json();
    const p = data.profile;
    if (!p) {{
      el.innerHTML =
        '<div style="background:#f3f7fc;border:1px solid #d6e1f1;border-radius:10px;padding:22px 24px;text-align:center;">' +
          '<div style="font-size:36px;line-height:1;margin-bottom:8px;">📄</div>' +
          '<div style="font-size:15px;font-weight:600;color:#5C5CD6;margin-bottom:6px;">No skills profile yet</div>' +
          '<div style="font-size:13px;color:#555;margin-bottom:16px;line-height:1.5;">Upload your resume (PDF or Word) and our AI will extract your target roles, industries, skills, technologies, and regulations — so the dashboard only shows jobs that actually match you.</div>' +
          '<button class="btn primary" onclick="setResumeTab(\\'upload\\')" style="padding:10px 22px;font-size:13.5px;">Upload your resume →</button>' +
        '</div>';
      // Hide Edit/Regenerate buttons — nothing to edit or regenerate yet.
      if (actions) actions.style.display = 'none';
      return;
    }}
    el.innerHTML = _renderProfileHTML(p);
    if (actions) actions.style.display = 'flex';
  }} catch (e) {{
    el.innerHTML = '<p style="font-size:13px;color:#b00;">Failed to load: ' + (e.message || e) + '</p>';
    if (actions) actions.style.display = 'none';
  }}
}}

function _renderProfileHTML(p) {{
  function section(title, items, color, fieldKey) {{
    items = items || [];
    const chips = items.map(s => {{
      const safe = _esc(s);
      const jsSafe = String(s).replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
      return '<span style="display:inline-flex;align-items:center;background:' + color + ';color:#5C5CD6;padding:3px 4px 3px 9px;border-radius:12px;font-size:11.5px;margin:2px 4px 2px 0;font-weight:500;">' +
             safe +
             (fieldKey ? '<button onclick="removeChip(\\''+ fieldKey +'\\', \\''+ jsSafe +'\\')" style="background:none;border:0;color:#888;cursor:pointer;padding:0 0 0 6px;font-size:14px;line-height:1;font-weight:600;" title="Remove">&times;</button>' : '') +
             '</span>';
    }}).join('');
    const addBtn = fieldKey
      ? '<button onclick="addChip(\\''+ fieldKey +'\\')" style="display:inline-block;background:#fafbfc;border:1px dashed #c0c8d4;color:#5C5CD6;padding:3px 11px;border-radius:12px;font-size:11.5px;cursor:pointer;font-weight:500;margin:2px 4px 2px 0;">+ Add</button>'
      : '';
    const count = items.length > 0 ? (' <span style="color:#999;font-weight:500;">· ' + items.length + '</span>') : '';
    return '<div style="margin-bottom:12px;"><div style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">' + title + count + '</div><div>' + chips + addBtn + '</div></div>';
  }}
  let html = '';
  if (p.primaryRole) html += '<div style="font-size:14px;color:#5C5CD6;font-weight:600;margin-bottom:4px;">' + _esc(p.primaryRole) + '</div>';
  if (p.summary) html += '<div style="font-size:13px;color:#555;margin-bottom:14px;line-height:1.45;">' + _esc(p.summary) + '</div>';
  html += '<div style="background:#f8f9fb;padding:14px 16px;border-radius:8px;border:1px solid #e6e8eb;">';
  if (p.seniorityLevel) html += '<div style="font-size:12px;color:#777;margin-bottom:8px;">Seniority: <strong style="color:#333;">' + _esc(p.seniorityLevel) + '</strong>' + (p.salaryFloor ? ' · Salary floor ~$' + Number(p.salaryFloor).toLocaleString() : '') + (p.remotePreferred ? ' · Remote preferred' : '') + '</div>';
  html += section('Target titles', p.targetTitles, '#e6f0ff', 'targetTitles');
  html += section('Industries', p.industries, '#e6fff0', 'industries');
  html += section('Specialties', p.specialties, '#f3e6ff', 'specialties');
  html += section('Key skills', p.keywords, '#fff8e1', 'keywords');
  html += section('Technologies', p.technologies, '#e8f4ff', 'technologies');
  html += section('Frameworks', p.frameworks, '#fff3d6', 'frameworks');
  html += section('Regulations', p.regulations, '#fff0e6', 'regulations');
  html += section('Certifications', p.certifications, '#e6fff8', 'certifications');
  html += section('Preferred locations', p.preferredLocations, '#e6f0ff', 'preferredLocations');
  if (p.remotePreference) {{
    const remoteLabel = ({{'remote-only':'Remote only','hybrid':'Hybrid OK','onsite':'Onsite preferred','any':'Any'}})[p.remotePreference] || p.remotePreference;
    html += section('Remote preference', [remoteLabel], '#ffe6f0', 'remotePreference');
  }} else {{
    html += section('Remote preference', [], '#ffe6f0', 'remotePreference');
  }}
  html += section('Target companies (AI suggested)', (p.targetCompanies||[]).map(function(c){{ return typeof c==='string' ? c : (c.name + (c.atsHint && c.atsHint !== 'unknown' ? ' ('+c.atsHint+')' : '')); }}), '#fef3e8', 'targetCompanies');
  html += section('Filtered out', p.negativeKeywords, '#ffe6e6', 'negativeKeywords');
  html += '</div>';
  if (p.generatedAt) html += '<div style="font-size:11px;color:#999;margin-top:8px;">Generated ' + new Date(p.generatedAt).toLocaleString() + '</div>';
  return html;
}}

const EDITABLE_FIELDS = [
  ['industries', 'Industries'],
  ['specialties', 'Specialties'],
  ['keywords', 'Key skills'],
  ['technologies', 'Technologies'],
  ['frameworks', 'Frameworks'],
  ['regulations', 'Regulations'],
  ['certifications', 'Certifications'],
  ['targetTitles', 'Target titles'],
  ['preferredLocations', 'Preferred locations'],
  ['negativeKeywords', 'Filtered-out terms'],
];

let _currentProfile = null;

function openEditProfileModal() {{
  // Load current profile then render the editor
  fetch(PROFILE_WORKER_URL).then(r => r.json()).then(data => {{
    const p = data.profile || {{}};
    _currentProfile = p;
    const container = document.getElementById('edit-profile-fields');
    container.innerHTML = '';
    EDITABLE_FIELDS.forEach(([key, label]) => {{
      const wrap = document.createElement('div');
      wrap.style.cssText = 'margin-bottom:12px;';
      const labelEl = document.createElement('label');
      labelEl.style.cssText = 'display:block; font-size:12px; font-weight:600; color:#555; margin-bottom:4px;';
      labelEl.textContent = label;
      const input = document.createElement('textarea');
      input.id = 'edit-' + key;
      input.rows = key === 'keywords' || key === 'specialties' ? 3 : 2;
      input.style.cssText = 'width:100%; box-sizing:border-box; padding:7px 10px; font-size:12.5px; border:1px solid #ccd0d6; border-radius:6px; font-family:inherit; resize:vertical;';
      input.value = (Array.isArray(p[key]) ? p[key] : []).join(', ');
      input.placeholder = 'comma-separated, e.g. nist csf, hipaa, iso 27001';
      wrap.appendChild(labelEl);
      wrap.appendChild(input);
      container.appendChild(wrap);
    }});
    document.getElementById('edit-profile-status').textContent = '';
    document.getElementById('edit-profile-overlay').style.display = 'flex';
  }}).catch(e => {{
    alert('Could not load current profile: ' + (e.message || e));
  }});
}}

function closeEditProfileModal() {{
  document.getElementById('edit-profile-overlay').style.display = 'none';
}}

async function saveProfileEdits() {{
  const editKey = getEditKey();
  if (!editKey) return;
  const statusEl = document.getElementById('edit-profile-status');
  statusEl.style.color = '#555';
  statusEl.textContent = 'Saving…';
  const patchFields = {{}};
  EDITABLE_FIELDS.forEach(([key]) => {{
    const v = (document.getElementById('edit-' + key).value || '').trim();
    patchFields[key] = v ? v.split(/[,;\\n]/).map(s => s.trim()).filter(Boolean) : [];
  }});
  try {{
    const r = await fetch(PROFILE_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ patchFields }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      statusEl.style.color = '#b00';
      statusEl.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      return;
    }}
    statusEl.style.color = '#0a6b3a';
    statusEl.textContent = 'Saved. Refreshing dashboard…';
    loadProfile();
    // Trigger refresh so new chips affect filtering
    try {{ await fetch(WORKER_BASE + '/refresh', {{ method: 'POST' }}); }} catch (e) {{ /* ignore */ }}
    setTimeout(() => {{ closeEditProfileModal(); window.location.reload(); }}, 180000);
  }} catch (e) {{
    statusEl.style.color = '#b00';
    statusEl.textContent = 'Failed: ' + (e.message || e);
  }}
}}

async function _patchProfileField(fieldKey, newArray) {{
  const editKey = getEditKey();
  if (!editKey) return false;
  const r = await fetch(PROFILE_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify({{ patchFields: {{ [fieldKey]: newArray }} }}),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{
    if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
    alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
    return false;
  }}
  return true;
}}

async function removeChip(fieldKey, value) {{
  if (!confirm('Remove "' + value + '" from your profile?')) return;
  // Read latest profile, drop the item, patch back
  const r = await fetch(PROFILE_WORKER_URL);
  const data = await r.json();
  const profile = data.profile || {{}};
  const existing = Array.isArray(profile[fieldKey]) ? profile[fieldKey] : [];
  const filtered = existing.filter(x => String(x).toLowerCase() !== String(value).toLowerCase());
  if (await _patchProfileField(fieldKey, filtered)) loadProfile();
}}

async function addChip(fieldKey) {{
  const input = prompt('Add to ' + fieldKey + ' (comma-separated for multiple):');
  if (!input) return;
  const additions = input.split(/[,;\\n]/).map(s => s.trim()).filter(Boolean);
  if (!additions.length) return;
  const r = await fetch(PROFILE_WORKER_URL);
  const data = await r.json();
  const profile = data.profile || {{}};
  const existing = Array.isArray(profile[fieldKey]) ? profile[fieldKey] : [];
  const merged = existing.slice();
  const seen = new Set(merged.map(x => String(x).toLowerCase()));
  for (const a of additions) {{
    const al = a.toLowerCase();
    if (!seen.has(al)) {{ merged.push(al); seen.add(al); }}
  }}
  if (await _patchProfileField(fieldKey, merged)) loadProfile();
}}

async function regenerateProfile(btn) {{
  const status = document.getElementById('regen-profile-status');
  const editKey = getEditKey();
  if (!editKey) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = 'Regenerating…';
  status.textContent = '';
  status.style.color = '#555';
  try {{
    const r = await fetch(PROFILE_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      status.style.color = '#b00';
      status.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    status.style.color = '#0a6b3a';
    status.textContent = 'Regenerated. Refreshing dashboard…';
    btn.textContent = orig;
    btn.disabled = false;
    loadProfile();
    // Trigger dashboard refresh so the richer profile starts filtering jobs
    try {{ await fetch(WORKER_BASE + '/refresh', {{ method: 'POST' }}); }} catch (e) {{ /* ignore */ }}
    setTimeout(() => window.location.reload(), 180000);
  }} catch (e) {{
    status.style.color = '#b00';
    status.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

async function openResumeModal() {{
  const modal = document.getElementById('resume-modal');
  const statusEl = document.getElementById('resume-status');
  const editor = document.getElementById('resume-editor');
  const textarea = document.getElementById('resume-text');
  document.getElementById('resume-save-status').textContent = '';
  document.getElementById('upload-status').textContent = '';
  document.getElementById('dropzone-label').textContent = 'Click to choose a file';
  document.getElementById('parse-resume-btn').disabled = true;
  _pendingUploadFile = null;
  statusEl.className = 'prep-status';
  statusEl.textContent = 'Loading…';
  statusEl.style.display = 'block';
  editor.style.display = 'none';
  modal.classList.add('show');
  try {{
    const r = await fetch(RESUME_WORKER_URL);
    const data = await r.json();
    if (data.error) {{
      statusEl.className = 'prep-status error';
      statusEl.textContent = 'Error loading resume: ' + data.error;
      return;
    }}
    textarea.value = data.resume || '';
    statusEl.style.display = 'none';
    editor.style.display = 'block';
    setResumeTab('upload');
    if (!data.resume) {{
      document.getElementById('upload-status').textContent = 'No resume saved yet — upload one to begin.';
    }}
  }} catch (e) {{
    statusEl.className = 'prep-status error';
    statusEl.textContent = 'Error loading resume: ' + (e.message || e);
  }}
}}

function closeResumeModal() {{
  document.getElementById('resume-modal').classList.remove('show');
}}

// --- File upload + browser-side text extraction -----------------------
function _wireResumeDropzone() {{
  const dz = document.getElementById('resume-dropzone');
  const input = document.getElementById('resume-file-input');
  if (!dz || !input || dz._wired) return;
  dz._wired = true;
  input.addEventListener('change', (e) => {{
    if (e.target.files && e.target.files[0]) _handleFileChosen(e.target.files[0]);
  }});
  ['dragover','dragenter'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.add('drag'); }}));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.remove('drag'); }}));
  dz.addEventListener('drop', (e) => {{
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) _handleFileChosen(e.dataTransfer.files[0]);
  }});
}}

function _handleFileChosen(file) {{
  const name = (file.name || '').toLowerCase();
  if (name.endsWith('.doc') && !name.endsWith('.docx')) {{
    document.getElementById('upload-status').textContent = 'Legacy .doc files are not supported. Open in Word → File → Save As → Word Document (.docx), then upload that.';
    return;
  }}
  if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {{
    document.getElementById('upload-status').textContent = 'Unsupported file. Use PDF or Word (.docx).';
    return;
  }}
  _pendingUploadFile = file;
  document.getElementById('dropzone-label').textContent = file.name;
  document.getElementById('parse-resume-btn').disabled = false;
  document.getElementById('upload-status').textContent = 'Ready. Click Parse & Save.';
}}

async function _extractText(file) {{
  const name = (file.name || '').toLowerCase();
  if (name.endsWith('.docx')) {{
    const buf = await file.arrayBuffer();
    const res = await window.mammoth.extractRawText({{ arrayBuffer: buf }});
    return (res && res.value || '').trim();
  }}
  if (name.endsWith('.pdf')) {{
    if (!window.pdfjsLib) throw new Error('PDF parser failed to load.');
    const buf = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({{ data: buf }}).promise;
    let out = '';
    for (let i = 1; i <= pdf.numPages; i++) {{
      const page = await pdf.getPage(i);
      const tc = await page.getTextContent();
      out += tc.items.map(it => it.str).join(' ') + '\\n\\n';
    }}
    return out.trim();
  }}
  throw new Error('Unsupported file type.');
}}

async function parseUploadedResume(btn) {{
  if (!_pendingUploadFile) return;
  const statusEl = document.getElementById('upload-status');
  const editKey = getEditKey();
  if (!editKey) return;
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Reading file…';
  statusEl.textContent = '';
  try {{
    const text = await _extractText(_pendingUploadFile);
    if (!text || text.length < 80) {{
      statusEl.textContent = 'Could not extract text from this file. Try saving as .docx, or use Edit JSON tab.';
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    btn.textContent = 'Parsing with Claude…';
    const r = await fetch(PARSE_RESUME_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ text, filename: _pendingUploadFile.name }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      statusEl.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    statusEl.textContent = 'Saved as new version (' + (data.version && data.version.label || 'new') + ') and activated.';
    if (data.parsed) {{
      const ta = document.getElementById('resume-text');
      if (ta) ta.value = JSON.stringify(data.parsed, null, 2);
    }}
    btn.textContent = orig;
    btn.disabled = false;
    _pendingUploadFile = null;
    document.getElementById('resume-file-input').value = '';
    document.getElementById('dropzone-label').textContent = 'Upload another to replace';
  }} catch (e) {{
    statusEl.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- Versions list ------------------------------------------------------
async function loadVersions() {{
  const list = document.getElementById('versions-list');
  list.innerHTML = '<p style="font-size:12px;color:#888;">Loading versions…</p>';
  try {{
    const r = await fetch(VERSIONS_WORKER_URL);
    const data = await r.json();
    if (data.error) {{
      list.innerHTML = '<p style="font-size:12px;color:#b00;">Error: ' + data.error + '</p>';
      return;
    }}
    const versions = data.versions || [];
    const activeId = data.activeId;
    if (!versions.length) {{
      list.innerHTML = '<p style="font-size:12px;color:#888;">No versions yet. Upload a file or paste JSON to create one.</p>';
      return;
    }}
    list.innerHTML = versions.map(v => {{
      const isActive = v.id === activeId;
      const dt = new Date(v.savedAt);
      const when = isNaN(dt) ? v.savedAt : dt.toLocaleString();
      const src = v.sourceType === 'upload' ? 'uploaded' : 'JSON paste';
      return '<div class="version-row' + (isActive ? ' active' : '') + '">' +
             '<div class="version-main">' +
             '<div class="version-label">' + _esc(v.label) + (isActive ? ' <span class="version-badge">Active</span>' : '') + '</div>' +
             '<div class="version-meta">' + src + ' · ' + when + '</div>' +
             '</div>' +
             '<div class="version-actions">' +
             (isActive ? '' : '<button class="v-btn primary" onclick="activateVersion(\\''+ v.id +'\\')">Activate</button>') +
             '<button class="v-btn" onclick="previewVersion(\\''+ v.id +'\\')">Preview</button>' +
             '<button class="v-btn" onclick="renameVersion(\\''+ v.id +'\\', \\''+ _esc(v.label).replace(/'/g,"\\\\'") +'\\')">Rename</button>' +
             (isActive ? '' : '<button class="v-btn danger" onclick="deleteVersion(\\''+ v.id +'\\')">Delete</button>') +
             '</div></div>';
    }}).join('');
  }} catch (e) {{
    list.innerHTML = '<p style="font-size:12px;color:#b00;">Error: ' + (e.message || e) + '</p>';
  }}
}}

function _esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

async function _versionAction(action, body) {{
  const editKey = getEditKey();
  if (!editKey) return null;
  const r = await fetch(VERSIONS_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify(body),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{
    if (r.status === 401) localStorage.removeItem('htj_resume_key');
    alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
    return null;
  }}
  return data;
}}

async function activateVersion(id) {{
  const data = await _versionAction('activate', {{ action: 'activate', id }});
  if (!data) return;
  // Update UI immediately
  loadVersions();
  // Auto-trigger a dashboard refresh so the user actually sees the change.
  // Without this, Activate seems to "do nothing" since the visible dashboard
  // is a pre-generated static HTML file.
  const list = document.getElementById('versions-list');
  if (list) {{
    const banner = document.createElement('div');
    banner.style.cssText = 'background:#fff8e1;border:1px solid #f6c93b;border-radius:6px;padding:10px 12px;margin:8px 0 0 0;font-size:13px;color:#5a4400;';
    banner.innerHTML = 'Activated. Refreshing your dashboard — page will reload automatically in about 3 minutes.';
    list.appendChild(banner);
  }}
  try {{
    await fetch(WORKER_BASE + '/refresh', {{ method: 'POST' }});
  }} catch (e) {{ /* ignore — page reload below still helps */ }}
  // Auto-reload after the GH Action should have finished (3 min is a safe estimate)
  setTimeout(() => window.location.reload(), 180000);
}}

async function deleteVersion(id) {{
  if (!confirm('Delete this version? This cannot be undone.')) return;
  const data = await _versionAction('delete', {{ action: 'delete', id }});
  if (data) loadVersions();
}}

async function previewVersion(id) {{
  const editKey = getEditKey();
  if (!editKey) return;
  const r = await fetch(VERSIONS_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify({{ action: 'get', id }}),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{ alert('Failed: ' + (data.error || ('HTTP ' + r.status))); return; }}
  setResumeTab('json');
  const ta = document.getElementById('resume-text');
  if (ta) ta.value = data.resume || '';
  document.getElementById('resume-save-status').textContent = 'Previewing version. Save to create a new version from this content.';
}}

async function renameVersion(id, currentLabel) {{
  const label = prompt('New label for this version:', currentLabel || '');
  if (label == null) return;
  const data = await _versionAction('rename', {{ action: 'rename', id, label }});
  if (data) loadVersions();
}}

async function saveResume(btn) {{
  const textarea = document.getElementById('resume-text');
  const statusEl = document.getElementById('resume-save-status');
  const value = textarea.value.trim();
  if (!value) {{
    statusEl.textContent = 'Resume is empty — paste content first.';
    return;
  }}
  // Light validation: should be JSON with a personal section
  try {{
    const parsed = JSON.parse(value);
    if (!parsed.personal) throw new Error('Resume JSON should include a "personal" key.');
  }} catch (e) {{
    if (!confirm('This does not look like valid resume JSON (' + e.message + '). Save anyway?')) return;
  }}
  const editKey = getEditKey();
  if (!editKey) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = 'Saving…';
  statusEl.textContent = '';
  try {{
    // Default label is timestamp so users don't accidentally save the example text
    const now = new Date();
    const defaultLabel = 'Manual edit — ' + now.toLocaleDateString();
    const label = prompt('Label for this version:', defaultLabel) || defaultLabel;
    const r = await fetch(RESUME_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ resume: value, label, sourceType: 'json-paste' }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      statusEl.textContent = 'Save failed: ' + (data.error || ('HTTP ' + r.status));
      btn.disabled = false;
      btn.textContent = orig;
      return;
    }}
    statusEl.textContent = 'Saved as new version.';
    btn.textContent = orig;
    btn.disabled = false;
  }} catch (e) {{
    statusEl.textContent = 'Save failed: ' + (e.message || e);
    btn.disabled = false;
    btn.textContent = orig;
  }}
}}

// Wire dropzone after DOM is ready
if (document.readyState !== 'loading') _wireResumeDropzone();
else document.addEventListener('DOMContentLoaded', _wireResumeDropzone);

// --- Refresh data (triggers GitHub Action via Cloudflare Worker) --------
const REFRESH_WORKER_URL = WORKER_BASE + '/refresh';

async function refreshData() {{
  const btn = document.getElementById('refresh-btn');
  if (!btn) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Triggering refresh…';
  try {{
    const r = await fetch(REFRESH_WORKER_URL, {{ method: 'POST' }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      btn.textContent = 'Refresh failed';
      alert('Refresh failed: ' + (data.error || ('HTTP ' + r.status)) + (data.details ? '\\n' + data.details : ''));
      setTimeout(() => {{ btn.textContent = original; btn.disabled = false; }}, 3000);
      return;
    }}
  }} catch (e) {{
    btn.textContent = 'Refresh failed';
    alert('Refresh failed: ' + (e.message || e));
    setTimeout(() => {{ btn.textContent = original; btn.disabled = false; }}, 3000);
    return;
  }}
  // Countdown then reload
  let secs = 150;
  const tick = () => {{
    btn.textContent = `Fetching jobs… ${{secs}}s, page will reload`;
    secs--;
    if (secs <= 0) {{
      window.location.reload();
    }} else {{
      setTimeout(tick, 1000);
    }}
  }};
  tick();
}}

// --- Prep modal (calls Cloudflare Worker for AI generation) -------------
const PREP_WORKER_URL = WORKER_BASE + '/prep' + USER_QS;

async function prepApplication(fp, btn) {{
  const card = btn.closest('.card');
  const titleEl = card.querySelector('.title a');
  const jobTitle = (titleEl?.textContent || '').trim();
  const company = (card.querySelector('.company')?.textContent || '').trim();
  const jobUrl = titleEl?.href || '';
  const jobDescription = (card.querySelector('.desc')?.textContent || '').trim();

  const modal = document.getElementById('prep-modal');
  const statusEl = document.getElementById('prep-status');
  const outputEl = document.getElementById('prep-output');
  const titleH = document.getElementById('prep-modal-title');

  titleH.textContent = `Materials for ${{jobTitle}} @ ${{company}}`;
  statusEl.className = 'prep-status';
  statusEl.textContent = 'Generating with Claude… this takes 10–30 seconds.';
  statusEl.style.display = 'block';
  outputEl.style.display = 'none';
  modal.classList.add('show');

  try {{
    const r = await fetch(PREP_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ jobTitle, company, jobDescription, jobUrl }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      statusEl.className = 'prep-status error';
      statusEl.textContent = `Error: ${{data.error || ('HTTP ' + r.status)}}${{data.details ? ' — ' + data.details : ''}}`;
      return;
    }}
    document.getElementById('prep-summary').textContent = data.summary || '(no summary returned)';
    document.getElementById('prep-cover').textContent = data.coverLetter || '(no cover letter returned)';
    document.getElementById('prep-linkedin').textContent = data.linkedin || '(no LinkedIn intro returned)';
    _tailoredResume = data.tailoredResume || null;
    _tailoredJobMeta = {{ jobTitle, company }};
    const tailoredSection = document.getElementById('prep-resume-section');
    if (_tailoredResume && _tailoredResume.personal) {{
      document.getElementById('prep-resume-preview').innerHTML = _renderResumeHTML(_tailoredResume);
      tailoredSection.style.display = 'block';
    }} else {{
      tailoredSection.style.display = 'none';
    }}
    statusEl.style.display = 'none';
    outputEl.style.display = 'block';
    // Auto-save the prep kit to the tracker so user can re-open without regenerating
    const kit = {{ summary: data.summary, coverLetter: data.coverLetter, linkedin: data.linkedin, tailoredResume: data.tailoredResume }};
    if (getEditKey()) {{
      _trackerAction('savePrepKit', {{ fp, jobMeta: {{ title: jobTitle, company, url: jobUrl }}, prepKit: kit }}).then(r => {{
        if (r && r.record) _trackerCache[fp] = r.record;
      }});
    }}
  }} catch (e) {{
    statusEl.className = 'prep-status error';
    statusEl.textContent = `Error: ${{e.message || e}}`;
  }}
}}
function closeModal() {{ document.getElementById('prep-modal').classList.remove('show'); }}
function copyPrepField(id, btn) {{
  const txt = document.getElementById(id).textContent;
  navigator.clipboard.writeText(txt).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

// --- Tailored resume rendering + downloads ----------------------------
let _tailoredResume = null;
let _tailoredJobMeta = {{ jobTitle: '', company: '' }};

function _escHtml(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

function _renderResumeHTML(r) {{
  if (!r || !r.personal) return '';
  const p = r.personal || {{}};
  const contact = [p.location, p.phone, p.email, p.linkedin].filter(Boolean).map(x => _escHtml(x)).join(' &nbsp;·&nbsp; ');
  let html = '';
  html += '<div style="text-align:center; margin-bottom:14px;">';
  html += '<div style="font-size:20px; font-weight:700; color:#5C5CD6; letter-spacing:0.3px;">' + _escHtml(p.name || '') + '</div>';
  if (contact) html += '<div style="font-size:11.5px; color:#555; margin-top:4px;">' + contact + '</div>';
  html += '</div>';
  if (r.summary) {{
    html += '<div style="margin-bottom:12px;">' + _escHtml(r.summary) + '</div>';
  }}
  if (r.skills && r.skills.length) {{
    html += '<div style="margin-bottom:14px;"><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Core Skills</div>';
    html += '<div style="font-size:12.5px;">' + r.skills.map(s => _escHtml(s)).join(' &nbsp;·&nbsp; ') + '</div></div>';
  }}
  if (r.experience && r.experience.length) {{
    html += '<div style="margin-bottom:14px;"><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Experience</div>';
    r.experience.forEach(exp => {{
      html += '<div style="margin-bottom:10px;">';
      html += '<div style="display:flex; justify-content:space-between; gap:10px;"><div><strong>' + _escHtml(exp.title || '') + '</strong> — ' + _escHtml(exp.company || '') + (exp.location ? '<span style="color:#666;"> (' + _escHtml(exp.location) + ')</span>' : '') + '</div>';
      html += '<div style="color:#666; font-size:11.5px; white-space:nowrap;">' + _escHtml(exp.start || '') + ' – ' + _escHtml(exp.end || '') + '</div></div>';
      if (exp.bullets && exp.bullets.length) {{
        html += '<ul style="margin:4px 0 0 18px; padding:0;">';
        exp.bullets.forEach(b => {{ html += '<li style="margin-bottom:2px;">' + _escHtml(b) + '</li>'; }});
        html += '</ul>';
      }}
      html += '</div>';
    }});
    html += '</div>';
  }}
  if (r.education && r.education.length) {{
    html += '<div style="margin-bottom:12px;"><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Education</div>';
    r.education.forEach(ed => {{
      const line = [ed.degree, ed.field].filter(Boolean).join(' in ');
      html += '<div style="margin-bottom:4px;">' + _escHtml(line) + (ed.school ? ' — ' + _escHtml(ed.school) : '') + (ed.year ? ' <span style="color:#666;">(' + _escHtml(ed.year) + ')</span>' : '') + '</div>';
    }});
    html += '</div>';
  }}
  if (r.certifications && r.certifications.length) {{
    html += '<div><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Certifications</div>';
    html += '<div>' + r.certifications.map(c => _escHtml(c)).join(' &nbsp;·&nbsp; ') + '</div></div>';
  }}
  return html;
}}

function _resumeToText(r) {{
  if (!r || !r.personal) return '';
  const p = r.personal || {{}};
  const lines = [];
  lines.push((p.name || '').toUpperCase());
  const contact = [p.location, p.phone, p.email, p.linkedin].filter(Boolean).join(' · ');
  if (contact) lines.push(contact);
  lines.push('');
  if (r.summary) {{ lines.push('SUMMARY'); lines.push(r.summary); lines.push(''); }}
  if (r.skills && r.skills.length) {{ lines.push('CORE SKILLS'); lines.push(r.skills.join(' · ')); lines.push(''); }}
  if (r.experience && r.experience.length) {{
    lines.push('EXPERIENCE');
    r.experience.forEach(exp => {{
      const dates = [exp.start, exp.end].filter(Boolean).join(' – ');
      lines.push((exp.title || '') + ' — ' + (exp.company || '') + (exp.location ? ' (' + exp.location + ')' : '') + (dates ? '  [' + dates + ']' : ''));
      (exp.bullets || []).forEach(b => lines.push('  • ' + b));
      lines.push('');
    }});
  }}
  if (r.education && r.education.length) {{
    lines.push('EDUCATION');
    r.education.forEach(ed => {{
      const line = [ed.degree, ed.field].filter(Boolean).join(' in ');
      lines.push(line + (ed.school ? ' — ' + ed.school : '') + (ed.year ? ' (' + ed.year + ')' : ''));
    }});
    lines.push('');
  }}
  if (r.certifications && r.certifications.length) {{
    lines.push('CERTIFICATIONS');
    lines.push(r.certifications.join(' · '));
  }}
  return lines.join('\\n');
}}

function _resumeFilename(ext) {{
  const company = (_tailoredJobMeta.company || 'company').replace(/[^a-z0-9]+/gi,'_').replace(/^_|_$/g,'').slice(0, 30);
  const name = (_tailoredResume && _tailoredResume.personal && _tailoredResume.personal.name) ? _tailoredResume.personal.name.replace(/[^a-z0-9]+/gi,'_').replace(/^_|_$/g,'') : 'Resume';
  return name + '_' + company + '.' + ext;
}}

function copyTailoredResume(btn) {{
  if (!_tailoredResume) return;
  const text = _resumeToText(_tailoredResume);
  navigator.clipboard.writeText(text).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

function _buildPrintableHTML(r) {{
  // Letter-paper friendly HTML. Word opens HTML-with-.doc-extension natively.
  return `<!doctype html><html><head><meta charset="utf-8"><title>${{_escHtml((r.personal && r.personal.name) || 'Resume')}}</title>` +
         `<style>body{{font-family:Calibri,Arial,sans-serif;color:#222;font-size:11pt;line-height:1.4;margin:32px 40px;}}` +
         `h1{{font-size:18pt;margin:0 0 4px 0;color:#5C5CD6;text-align:center;letter-spacing:.5px;}}` +
         `.contact{{text-align:center;font-size:10pt;color:#555;margin-bottom:14px;}}` +
         `h2{{font-size:11pt;color:#5C5CD6;text-transform:uppercase;letter-spacing:.6px;border-bottom:1px solid #c0c8d4;padding-bottom:2px;margin:14px 0 6px 0;}}` +
         `.role{{display:flex;justify-content:space-between;gap:10px;font-weight:bold;margin-top:8px;}}` +
         `.dates{{color:#666;font-weight:normal;font-size:10pt;}}` +
         `ul{{margin:4px 0 0 20px;padding:0;}}li{{margin-bottom:2px;}}p{{margin:0 0 6px 0;}}` +
         `</style></head><body>` +
         _renderResumeForPrint(r) +
         `</body></html>`;
}}

function _renderResumeForPrint(r) {{
  const p = r.personal || {{}};
  const contact = [p.location, p.phone, p.email, p.linkedin].filter(Boolean).map(x => _escHtml(x)).join(' &nbsp;·&nbsp; ');
  let html = '';
  html += '<h1>' + _escHtml(p.name || '') + '</h1>';
  if (contact) html += '<div class="contact">' + contact + '</div>';
  if (r.summary) {{ html += '<h2>Summary</h2><p>' + _escHtml(r.summary) + '</p>'; }}
  if (r.skills && r.skills.length) {{ html += '<h2>Core Skills</h2><p>' + r.skills.map(s => _escHtml(s)).join(' &nbsp;·&nbsp; ') + '</p>'; }}
  if (r.experience && r.experience.length) {{
    html += '<h2>Experience</h2>';
    r.experience.forEach(exp => {{
      const dates = [exp.start, exp.end].filter(Boolean).map(x => _escHtml(x)).join(' – ');
      html += '<div class="role"><div>' + _escHtml(exp.title || '') + ' — ' + _escHtml(exp.company || '');
      if (exp.location) html += ' <span style="color:#666;font-weight:normal;">(' + _escHtml(exp.location) + ')</span>';
      html += '</div><div class="dates">' + dates + '</div></div>';
      if (exp.bullets && exp.bullets.length) {{
        html += '<ul>';
        exp.bullets.forEach(b => {{ html += '<li>' + _escHtml(b) + '</li>'; }});
        html += '</ul>';
      }}
    }});
  }}
  if (r.education && r.education.length) {{
    html += '<h2>Education</h2>';
    r.education.forEach(ed => {{
      const line = [ed.degree, ed.field].filter(Boolean).map(x => _escHtml(x)).join(' in ');
      html += '<p>' + line + (ed.school ? ' — ' + _escHtml(ed.school) : '') + (ed.year ? ' <span style="color:#666;">(' + _escHtml(ed.year) + ')</span>' : '') + '</p>';
    }});
  }}
  if (r.certifications && r.certifications.length) {{
    html += '<h2>Certifications</h2><p>' + r.certifications.map(c => _escHtml(c)).join(' &nbsp;·&nbsp; ') + '</p>';
  }}
  return html;
}}

async function downloadTailoredResume(format, btn) {{
  if (!_tailoredResume) return;
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Building…';
  try {{
    if (format === 'pdf') {{
      const html = _buildPrintableHTML(_tailoredResume);
      const container = document.createElement('div');
      container.innerHTML = html;
      // html2pdf needs the actual content node, not the full <html>
      const node = container.querySelector('body') ? container : container;
      await html2pdf().set({{
        margin: [10, 10, 10, 10],
        filename: _resumeFilename('pdf'),
        image: {{ type: 'jpeg', quality: 0.98 }},
        html2canvas: {{ scale: 2, useCORS: true }},
        jsPDF: {{ unit: 'mm', format: 'letter', orientation: 'portrait' }},
        pagebreak: {{ mode: ['css', 'legacy'] }},
      }}).from(node).save();
    }} else if (format === 'doc') {{
      const html = _buildPrintableHTML(_tailoredResume);
      // Use MIME type Word recognises for HTML; saved as .doc opens directly in Word.
      const blob = new Blob(['\\ufeff' + html], {{ type: 'application/msword' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = _resumeFilename('doc');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }}
    btn.textContent = 'Downloaded!';
    setTimeout(() => {{ btn.textContent = orig; btn.disabled = false; }}, 1500);
  }} catch (e) {{
    alert('Download failed: ' + (e.message || e));
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- LinkedIn Contacts feature ----------------------------------------
const LINKEDIN_CONTACTS_KEY = 'htj_linkedin_contacts_' + USER_SLUG;
const LINKEDIN_CONTACTS_META_KEY = 'htj_linkedin_contacts_meta_' + USER_SLUG;
let _pendingContactsFile = null;
let _contactsByCompany = null; // {{ normalizedCompany: [contact, ...] }}

function _normalizeCompany(name) {{
  if (!name) return '';
  let s = String(name).toLowerCase().trim();
  // strip leading "the "
  s = s.replace(/^the\s+/, '');
  // strip trailing punctuation
  s = s.replace(/[.,;:!?]+$/g, '');
  // strip common legal suffixes (with or without comma/period)
  s = s.replace(/[,]?\s*(inc|incorporated|llc|l\.l\.c\.|corp|corporation|co|company|ltd|limited|gmbh|plc|holdings|group|partners)\s*\.?$/g, '');
  // collapse whitespace
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}}

function _companiesMatch(a, b) {{
  const na = _normalizeCompany(a);
  const nb = _normalizeCompany(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  // prefix/contains match — require shorter side >= 5 chars to avoid false positives
  const shorter = na.length <= nb.length ? na : nb;
  const longer = na.length <= nb.length ? nb : na;
  if (shorter.length < 5) return false;
  // word-boundary contains
  if (longer.startsWith(shorter + ' ') || longer.endsWith(' ' + shorter) || longer.includes(' ' + shorter + ' ')) return true;
  return false;
}}

// Parse a CSV line respecting quoted fields. Returns array of strings.
function _csvSplitLine(line) {{
  const out = [];
  let cur = '';
  let inQ = false;
  for (let i = 0; i < line.length; i++) {{
    const c = line[i];
    if (inQ) {{
      if (c === '"') {{
        if (line[i+1] === '"') {{ cur += '"'; i++; }}
        else inQ = false;
      }} else cur += c;
    }} else {{
      if (c === ',') {{ out.push(cur); cur = ''; }}
      else if (c === '"') inQ = true;
      else cur += c;
    }}
  }}
  out.push(cur);
  return out;
}}

// Parse a LinkedIn Connections.csv. Skips the "Notes:" preamble and any blank lines.
function _parseConnectionsCSV(text) {{
  if (!text) return [];
  // Normalize newlines
  const lines = text.replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n');
  // Find header row — must contain "First Name" and "Last Name"
  let headerIdx = -1;
  for (let i = 0; i < lines.length; i++) {{
    const lower = lines[i].toLowerCase();
    if (lower.includes('first name') && lower.includes('last name')) {{
      headerIdx = i;
      break;
    }}
  }}
  if (headerIdx === -1) throw new Error('Could not find the connections header row. Make sure this is the Connections.csv from your LinkedIn export.');
  const header = _csvSplitLine(lines[headerIdx]).map(h => h.trim().toLowerCase());
  const idx = {{
    first: header.indexOf('first name'),
    last: header.indexOf('last name'),
    url: header.indexOf('url'),
    email: header.indexOf('email address'),
    company: header.indexOf('company'),
    position: header.indexOf('position'),
    connected: header.indexOf('connected on'),
  }};
  const out = [];
  for (let i = headerIdx + 1; i < lines.length; i++) {{
    const ln = lines[i];
    if (!ln || !ln.trim()) continue;
    const cols = _csvSplitLine(ln);
    const first = (idx.first >= 0 ? cols[idx.first] : '') || '';
    const last = (idx.last >= 0 ? cols[idx.last] : '') || '';
    const company = (idx.company >= 0 ? cols[idx.company] : '') || '';
    if (!first && !last) continue; // skip empty rows
    out.push({{
      first: first.trim(),
      last: last.trim(),
      url: (idx.url >= 0 ? (cols[idx.url] || '').trim() : ''),
      email: (idx.email >= 0 ? (cols[idx.email] || '').trim() : ''),
      company: company.trim(),
      position: (idx.position >= 0 ? (cols[idx.position] || '').trim() : ''),
      connected: (idx.connected >= 0 ? (cols[idx.connected] || '').trim() : ''),
    }});
  }}
  return out;
}}

function loadLinkedInContacts() {{
  try {{
    const raw = localStorage.getItem(LINKEDIN_CONTACTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  }} catch (e) {{ return []; }}
}}

function loadLinkedInContactsMeta() {{
  try {{
    const raw = localStorage.getItem(LINKEDIN_CONTACTS_META_KEY);
    return raw ? JSON.parse(raw) : null;
  }} catch (e) {{ return null; }}
}}

function saveLinkedInContacts(contacts, filename) {{
  localStorage.setItem(LINKEDIN_CONTACTS_KEY, JSON.stringify(contacts));
  localStorage.setItem(LINKEDIN_CONTACTS_META_KEY, JSON.stringify({{
    count: contacts.length,
    uploadedAt: new Date().toISOString(),
    filename: filename || 'Connections.csv',
  }}));
  _contactsByCompany = null; // invalidate cache
}}

function clearLinkedInContacts() {{
  localStorage.removeItem(LINKEDIN_CONTACTS_KEY);
  localStorage.removeItem(LINKEDIN_CONTACTS_META_KEY);
  _contactsByCompany = null;
  injectContactBadgesOnCards(); // refresh badges
  renderContactsSummary();
  renderContactsList();
}}

function _buildContactsByCompany() {{
  if (_contactsByCompany) return _contactsByCompany;
  const contacts = loadLinkedInContacts();
  const map = {{}};
  contacts.forEach(c => {{
    const norm = _normalizeCompany(c.company);
    if (!norm) return;
    if (!map[norm]) map[norm] = [];
    map[norm].push(c);
  }});
  _contactsByCompany = map;
  return map;
}}

function _findContactsForCompany(displayCompany) {{
  const contacts = loadLinkedInContacts();
  if (!contacts.length) return [];
  const target = _normalizeCompany(displayCompany);
  if (!target) return [];
  const matched = [];
  const seen = new Set();
  for (const c of contacts) {{
    if (_companiesMatch(c.company, displayCompany)) {{
      const k = (c.first + '|' + c.last + '|' + c.url).toLowerCase();
      if (!seen.has(k)) {{ seen.add(k); matched.push(c); }}
    }}
  }}
  return matched;
}}

// --- Modal: upload / list ---------------------------------------------
function setContactsTab(tab) {{
  document.querySelectorAll('#contacts-modal .tab-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.ctab === tab);
  }});
  document.querySelectorAll('#contacts-modal .tab-panel').forEach(p => {{
    p.classList.toggle('active', p.id === 'ctab-' + tab);
  }});
  if (tab === 'list') renderContactsList();
}}

function openContactsModal() {{
  const modal = document.getElementById('contacts-modal');
  document.getElementById('contacts-upload-status').textContent = '';
  document.getElementById('contacts-dropzone-label').textContent = 'Click to choose your Connections.csv';
  document.getElementById('parse-contacts-btn').disabled = true;
  _pendingContactsFile = null;
  renderContactsSummary();
  setContactsTab('upload');
  modal.classList.add('show');
}}

function closeContactsModal() {{
  document.getElementById('contacts-modal').classList.remove('show');
}}

function renderContactsSummary() {{
  const wrap = document.getElementById('contacts-summary-wrap');
  if (!wrap) return;
  const meta = loadLinkedInContactsMeta();
  const contacts = loadLinkedInContacts();
  if (!contacts.length) {{
    wrap.innerHTML = '';
    return;
  }}
  const dt = meta && meta.uploadedAt ? new Date(meta.uploadedAt) : null;
  const dtStr = dt ? dt.toLocaleDateString(undefined, {{ year:'numeric', month:'short', day:'numeric' }}) : 'recently';
  wrap.innerHTML = '<div class="contact-summary"><span><b>' + contacts.length + '</b> contacts loaded · uploaded ' + dtStr + '</span><button class="clear-btn" onclick="if(confirm(\\'Clear all saved contacts?\\'))clearLinkedInContacts()">Clear</button></div>';
}}

function renderContactsList() {{
  const wrap = document.getElementById('contacts-list-wrap');
  if (!wrap) return;
  const contacts = loadLinkedInContacts();
  if (!contacts.length) {{
    wrap.innerHTML = '<p class="contact-empty">No contacts saved yet. Upload your Connections.csv on the first tab.</p>';
    return;
  }}
  // Group by company, sort by company then name
  const map = _buildContactsByCompany();
  const companies = Object.keys(map).sort();
  let html = '<p style="font-size:12px;color:#777;margin:0 0 10px 0;">Grouped by company. ' + companies.length + ' companies, ' + contacts.length + ' contacts.</p>';
  companies.forEach(normCo => {{
    const list = map[normCo].slice().sort((a,b) => (a.last||'').localeCompare(b.last||''));
    const display = list[0].company || normCo;
    html += '<div style="margin-bottom:14px;">';
    html += '<div style="font-weight:700;color:#5C5CD6;font-size:13px;margin-bottom:6px;">' + _escHtml(display) + ' <span style="color:#888;font-weight:normal;font-size:11px;">(' + list.length + ')</span></div>';
    list.forEach(c => {{
      const name = ((c.first || '') + ' ' + (c.last || '')).trim();
      html += '<div style="font-size:12.5px;color:#333;padding:4px 0 4px 10px;border-left:2px solid #eaf2fb;margin-bottom:3px;">';
      html += '<b>' + _escHtml(name) + '</b>';
      if (c.position) html += ' <span style="color:#666;">— ' + _escHtml(c.position) + '</span>';
      if (c.url) html += ' <a href="' + _escHtml(c.url) + '" target="_blank" style="color:#0a66c2;font-size:11px;margin-left:4px;">profile↗</a>';
      html += '</div>';
    }});
    html += '</div>';
  }});
  wrap.innerHTML = html;
}}

function _wireContactsDropzone() {{
  const dz = document.getElementById('contacts-dropzone');
  const input = document.getElementById('contacts-file-input');
  if (!dz || !input || dz._wired) return;
  dz._wired = true;
  input.addEventListener('change', (e) => {{
    if (e.target.files && e.target.files[0]) _handleContactsFileChosen(e.target.files[0]);
  }});
  ['dragover','dragenter'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.add('drag'); }}));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.remove('drag'); }}));
  dz.addEventListener('drop', (e) => {{
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) _handleContactsFileChosen(e.dataTransfer.files[0]);
  }});
}}

function _handleContactsFileChosen(file) {{
  const name = (file.name || '').toLowerCase();
  if (!name.endsWith('.csv')) {{
    document.getElementById('contacts-upload-status').textContent = 'Need a .csv file. Make sure you unzipped the LinkedIn archive and selected Connections.csv.';
    return;
  }}
  _pendingContactsFile = file;
  document.getElementById('contacts-dropzone-label').textContent = file.name;
  document.getElementById('parse-contacts-btn').disabled = false;
  document.getElementById('contacts-upload-status').textContent = 'Ready. Click Save contacts.';
}}

async function parseUploadedContacts(btn) {{
  if (!_pendingContactsFile) return;
  const statusEl = document.getElementById('contacts-upload-status');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Reading…';
  try {{
    const text = await _pendingContactsFile.text();
    const contacts = _parseConnectionsCSV(text);
    if (!contacts.length) {{
      statusEl.textContent = 'No contacts found in this file. Is this the right CSV?';
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    saveLinkedInContacts(contacts, _pendingContactsFile.name);
    statusEl.textContent = 'Saved ' + contacts.length + ' contacts. Badges will appear on matching jobs.';
    btn.textContent = orig;
    btn.disabled = false;
    _pendingContactsFile = null;
    document.getElementById('contacts-file-input').value = '';
    document.getElementById('contacts-dropzone-label').textContent = 'Upload another to replace';
    renderContactsSummary();
    renderContactsList();
    injectContactBadgesOnCards();
  }} catch (e) {{
    statusEl.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- Badge injection on job cards -------------------------------------
function injectContactBadgesOnCards() {{
  const cards = document.querySelectorAll('.card');
  if (!cards.length) return;
  const contacts = loadLinkedInContacts();
  cards.forEach(card => {{
    // Remove any existing badge first (so re-runs are clean)
    const existing = card.querySelector('.contact-badge');
    if (existing) existing.remove();
    if (!contacts.length) return;
    const companyEl = card.querySelector('.company');
    if (!companyEl) return;
    const company = (companyEl.textContent || '').trim();
    const matches = _findContactsForCompany(company);
    if (!matches.length) return;
    const badge = document.createElement('span');
    badge.className = 'contact-badge';
    const hiringCount = matches.filter(_isHiringRoleContact).length;
    if (hiringCount > 0) {{
      badge.classList.add('hiring');
      badge.title = hiringCount + ' recruiter/HR contact' + (hiringCount === 1 ? '' : 's') + ' + ' + (matches.length - hiringCount) + ' other at ' + company;
      badge.innerHTML = '<span class="ic">🎯</span> ' + hiringCount + ' recruiter' + (hiringCount === 1 ? '' : 's') + (matches.length > hiringCount ? ' (+ ' + (matches.length - hiringCount) + ')' : '');
    }} else {{
      badge.title = matches.length + ' of your LinkedIn contacts work at ' + company;
      badge.innerHTML = '<span class="ic">🤝</span> ' + matches.length + ' contact' + (matches.length === 1 ? '' : 's');
    }}
    badge.addEventListener('click', (e) => {{
      e.stopPropagation();
      const titleEl = card.querySelector('.title a');
      const jobTitle = titleEl ? (titleEl.textContent || '').trim() : '';
      const jobUrl = titleEl ? titleEl.getAttribute('href') : '';
      openCompanyContactsModal(company, jobTitle, jobUrl, matches);
    }});
    companyEl.parentNode.insertBefore(badge, companyEl.nextSibling);
  }});
  // Now that contact badges are in place, re-sort so contact-having
  // jobs bubble to the top.
  try {{ if (typeof sortCards === 'function') sortCards(); }} catch (e) {{}}
}}

// --- Per-company contacts modal ---------------------------------------
function _getSenderName() {{
  const h1 = document.querySelector('header h1');
  if (h1) {{
    const txt = h1.textContent || '';
    const m = txt.match(/^Jobs for\s+(.+)$/i);
    if (m) return m[1].trim();
  }}
  return USER_SLUG.charAt(0).toUpperCase() + USER_SLUG.slice(1);
}}

function _draftOutreachMessage(contact, company, jobTitle) {{
  const first = (contact.first || '').trim() || 'there';
  const sender = _getSenderName();
  const titlePart = jobTitle ? ('an opening for ' + jobTitle + ' at ' + company) : ('an opportunity at ' + company);
  return (
    'Hi ' + first + ',\\n\\n' +
    'Hope you\\'re doing well! I came across ' + titlePart + ' and noticed you\\'re on the team. ' +
    'Would you be open to a quick chat about your experience there? If it seems like a fit, I\\'d also really appreciate a referral or any thoughts on how to approach the application.\\n\\n' +
    'Happy to share my resume — thanks for considering!\\n\\n' +
    'Best,\\n' + sender
  );
}}

function openCompanyContactsModal(company, jobTitle, jobUrl, contacts) {{
  const modal = document.getElementById('company-contacts-modal');
  document.getElementById('company-contacts-title').textContent = contacts.length + ' contact' + (contacts.length === 1 ? '' : 's') + ' at ' + company;
  document.getElementById('company-contacts-sub').textContent = jobTitle ? ('For: ' + jobTitle) : 'People you know who work there.';
  const wrap = document.getElementById('company-contacts-list');
  let html = '';
  contacts.forEach((c, i) => {{
    const name = ((c.first || '') + ' ' + (c.last || '')).trim();
    const msg = _draftOutreachMessage(c, company, jobTitle);
    const msgId = 'msg-' + i;
    html += '<div class="contact-row">';
    html += '<div class="name-line"><span class="cname">' + _escHtml(name) + '</span>';
    if (c.position) html += '<span class="ctitle">' + _escHtml(c.position) + '</span>';
    html += '</div>';
    if (c.connected) html += '<div class="cmeta">Connected ' + _escHtml(c.connected) + '</div>';
    html += '<div class="msg-box" id="' + msgId + '">' + _escHtml(msg) + '</div>';
    html += '<div class="crow-actions">';
    html += '<button class="btn primary" onclick="copyContactMessage(\\'' + msgId + '\\', this)">Copy message</button>';
    if (c.url) {{
      html += '<a class="btn primary" href="' + _escHtml(c.url) + '" target="_blank" style="text-decoration:none;background:#0a66c2;border-color:#0a66c2;">Open profile on LinkedIn ↗</a>';
    }}
    if (c.email) {{
      const subj = encodeURIComponent('Quick question about ' + (jobTitle || company));
      const body = encodeURIComponent(msg);
      html += '<a class="btn" href="mailto:' + _escHtml(c.email) + '?subject=' + subj + '&body=' + body + '" style="text-decoration:none;background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;">Email instead</a>';
    }}
    html += '</div>';
    html += '</div>';
  }});
  wrap.innerHTML = html;
  modal.classList.add('show');
}}

function closeCompanyContactsModal() {{
  document.getElementById('company-contacts-modal').classList.remove('show');
}}

function copyContactMessage(elId, btn) {{
  const el = document.getElementById(elId);
  if (!el) return;
  const text = el.textContent || '';
  navigator.clipboard.writeText(text).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }}).catch(() => {{
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); }} catch (e) {{}}
    document.body.removeChild(ta);
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

// Wire contacts on DOM ready, and inject badges
if (document.readyState !== 'loading') {{
  _wireContactsDropzone();
  injectContactBadgesOnCards();
}} else {{
  document.addEventListener('DOMContentLoaded', () => {{
    _wireContactsDropzone();
    injectContactBadgesOnCards();
  }});
}}

// init
loadTracker().then(() => {{
  refreshTrackerUI();
  setView(viewMode);
  setEmploymentFilter(employmentFilter);
}});

// ============================================================
// First-login wizard
// ============================================================
const HAS_PROFILE_AT_RENDER = {has_profile_js};
const WIZ_USER_NAME = "{user_name}";

const WIZ_STEPS = [
  {{
    title: "Welcome to getmemyjob, " + WIZ_USER_NAME + ".",
    body: "<p>We'll set you up in about <strong>2 minutes</strong>. After that you'll see roles tailored to your background — no clinical, no sales, no junk.</p><p>Here's what we'll do:</p><ul><li>Upload your resume (PDF or Word)</li><li>Review the skills we extract from it</li><li>Optionally add your LinkedIn network for warm intros</li></ul>",
    cta: "Let&rsquo;s go",
    action: "next",
    skipText: "Skip for now"
  }},
  {{
    title: "Upload your resume",
    body: "<p>Drop a <strong>PDF or Word</strong> resume — we'll read it and figure out which roles to surface for you.</p><p>It takes about 10 seconds.</p>",
    cta: "Open resume upload &rarr;",
    action: "open-resume",
    skipText: "Skip — I'll do this later"
  }},
  {{
    title: "Adjust your target titles, industries and skills",
    body:
      '<p style="margin-bottom:12px;font-size:14px;color:#444;">These are extracted from your resume. We use them to match you against jobs \u2014 add anything we missed, remove anything inaccurate. <strong>Sharper signals = fewer 0-match days.</strong></p>' +
      '<div id="wiz-chip-status" style="font-size:12px;color:#888;margin-bottom:8px;min-height:16px;">Loading your profile\u2026</div>' +
      '<div data-field="targetTitles" class="wiz-chip-section" style="margin-bottom:14px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Target titles <span style="font-weight:400;color:#888;">&mdash; the job titles you actually want (this drives matching the most)</span></div>' +
        '<div class="wiz-chip-list" data-target="targetTitles" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;min-height:28px;"></div>' +
        '<div style="display:flex;gap:6px;">' +
          '<input class="wiz-chip-input" data-target="targetTitles" type="text" placeholder="Add a target title\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div data-field="industries" class="wiz-chip-section" style="margin-bottom:14px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Industries <span style="font-weight:400;color:#888;">\u2014 broad sectors (e.g. banking, fintech, healthcare-it)</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-industries" style="min-height:30px;"></div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
          '<input class="wiz-chip-input" data-target="industries" type="text" placeholder="Add an industry\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div data-field="keywords" class="wiz-chip-section" style="margin-bottom:14px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Key skills &amp; keywords <span style="font-weight:400;color:#888;">\u2014 must-have terms in job title/desc</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-keywords" style="min-height:30px;"></div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
          '<input class="wiz-chip-input" data-target="keywords" type="text" placeholder="Add a keyword\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div data-field="specialties" class="wiz-chip-section" style="margin-bottom:6px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Specialties <span style="font-weight:400;color:#888;">\u2014 granular sub-domains</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-specialties" style="min-height:30px;"></div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
          '<input class="wiz-chip-input" data-target="specialties" type="text" placeholder="Add a specialty\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div id="wiz-chip-save-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save changes &rarr;",
    action: "save-profile-chips",
    skipText: "Skip \u2014 use AI defaults"
  }},
  {{
    title: "Confirm where you want to work",
    body: '<p style="margin-bottom:14px;">We extracted these from your resume. Tweak them so they reflect what you\u2019re actually open to \u2014 we use them to filter jobs.</p>' +
      '<label for="wiz-locs" style="display:block;font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Preferred locations</label>' +
      '<input id="wiz-locs" type="text" placeholder="e.g. New York City, Remote (US)" style="width:100%;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:14px;margin-bottom:6px;">' +
      '<div style="font-size:12px;color:#888;margin-bottom:14px;">Comma-separated. Add &ldquo;Remote (US)&rdquo; if you\u2019re open to remote.</div>' +
      '<label for="wiz-remote" style="display:block;font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Remote preference</label>' +
      '<select id="wiz-remote" style="width:100%;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:14px;background:white;">' +
      '<option value="any">Any &mdash; show me everything</option>' +
      '<option value="remote-only">Remote only</option>' +
      '<option value="hybrid">Hybrid (remote OK, but I\u2019ll travel to office sometimes)</option>' +
      '<option value="onsite">Onsite preferred</option>' +
      '</select>' +
      '<div id="wiz-locs-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save preferences &rarr;",
    action: "save-location-remote",
    skipText: "Skip \u2014 use AI defaults"
  }},
  {{
    title: "What's your ideal mix of company sizes?",
    body: '<p style="margin-bottom:14px;">We mix jobs across startups, mid-size, and large employers. Tell us your ideal balance \u2014 drag the sliders or type a number. Total has to add up to 100. Set any one to 0 to exclude that size entirely.</p>' +
      '<div style="display:flex;flex-direction:column;gap:14px;">' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Startups</strong> <span style=\"color:#888;font-weight:normal;\">&mdash; under 500 employees, often early-stage</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-mix-startup-num" type="number" min="0" max="100" value="33" oninput="wizMixOnNum(\\'startup\\')" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-mix-startup" min="0" max="100" value="33" oninput="wizMixOnSlide(\\'startup\\')" style="width:100%;">' +'</div>' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Mid-size</strong> <span style=\"color:#888;font-weight:normal;\">&mdash; 500\u201310k employees, established</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-mix-midsize-num" type="number" min="0" max="100" value="33" oninput="wizMixOnNum(\\'midsize\\')" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-mix-midsize" min="0" max="100" value="33" oninput="wizMixOnSlide(\\'midsize\\')" style="width:100%;">' +'</div>' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Large</strong> <span style=\"color:#888;font-weight:normal;\">&mdash; 10k+ employees, Fortune 500 / public</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-mix-large-num" type="number" min="0" max="100" value="33" oninput="wizMixOnNum(\\'large\\')" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-mix-large" min="0" max="100" value="33" oninput="wizMixOnSlide(\\'large\\')" style="width:100%;">' +'</div>' +
      '</div>' +
      '<div id="wiz-mix-status" style="display:flex;justify-content:space-between;font-size:12px;color:#888;margin-top:10px;min-height:18px;">' +
      '<span>Total: <strong id="wiz-mix-sum-val">99</strong>%</span>' +
      '<span id="wiz-mix-msg"></span>' +
      '</div>',
    cta: "Save preferences &rarr;",
    action: "save-company-sizes",
    skipText: "Skip \u2014 use an even mix"
  }},
  {{
    title: "How many jobs do you want to apply to per day?",
    body: '<p style="margin-bottom:14px;">A daily goal keeps the job search consistent. You can change this anytime in Preferences.</p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">' +
      ['1','3','5','10','15','20'].map(function(n) {{
        return '<button type="button" class="wiz-quick-pick" data-n="' + n + '" onclick="wizPickDailyTarget(' + n + ')" style="padding:8px 14px;border:1px solid #d0d4dc;border-radius:8px;background:#fff;cursor:pointer;font-size:13px;font-weight:600;">' + n + '</button>';
      }}).join('') + '</div>' +
      '<label style="display:block;font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Or set a custom number</label>' +
      '<input id="wiz-daily-target" type="number" min="1" max="50" value="5" style="width:100%;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:14px;">' +
      '<div id="wiz-daily-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save target &rarr;",
    action: "save-daily-target",
    skipText: "Skip \u2014 default 5/day"
  }},
  {{
    title: "How recent should jobs be by default?",
    body: '<p style="margin-bottom:14px;">Older listings are often filled or ghost roles. We will default to this window when you load the dashboard \u2014 you can always change it with the pills above the job feed.</p>' +
      '<div style="display:flex;flex-direction:column;gap:8px;">' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="0" style="cursor:pointer;"> <span><strong>Last 24 hours</strong> &mdash; only show roles posted today</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="7" checked style="cursor:pointer;"> <span><strong>Last 7 days</strong> &mdash; freshest listings, best signal of active hiring</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="14" style="cursor:pointer;"> <span><strong>Last 2 weeks</strong> &mdash; balance freshness with broader pool</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="30" style="cursor:pointer;"> <span><strong>Last 30 days</strong> &mdash; widest reasonable pool</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="all" style="cursor:pointer;"> <span><strong>All jobs</strong> &mdash; show everything, sort handles freshness</span></label>' +
      '</div>' +
      '<div id="wiz-recency-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save default &rarr;",
    action: "save-recency-window",
    skipText: "Skip \u2014 default Last 7 days"
  }},
  {{
    title: "Add your LinkedIn network (optional)",
    body: "<p>Upload your LinkedIn connections (one CSV) and the job feed will show <strong>&#x1f91d; N contacts</strong> badges on companies where you have warm intros.</p><p>It's a 30-second optional step. You can also do this later.</p>",
    cta: "Add LinkedIn contacts &rarr;",
    action: "open-contacts",
    skipText: "Skip — I'll do this later"
  }},
  {{
    title: "You're all set.",
    body: "<p>We're matching jobs to your profile right now. Your tailored dashboard will appear after the next refresh (2–3 min).</p><p>Quick reminders:</p><ul><li><strong>Prep Application</strong> on any job &rarr; tailored cover letter + resume summary</li><li><strong>Refresh data</strong> in the header &rarr; trigger a fresh pull anytime</li><li><strong>?</strong> button in the header &rarr; replay this tour</li></ul>",
    cta: "Finish &amp; refresh my jobs",
    action: "finish",
    skipText: null
  }}
];

let wizCurrent = 0;

function wizShow() {{
  const o = document.getElementById("gmj-wizard");
  if (!o) return;
  o.classList.add("show");
  wizRender();
}}
function wizHide() {{
  const o = document.getElementById("gmj-wizard");
  if (o) o.classList.remove("show");
}}
function wizRender() {{
  const s = WIZ_STEPS[wizCurrent];
  document.getElementById("wiz-step-count").textContent = "Step " + (wizCurrent + 1) + " of " + WIZ_STEPS.length;
  // Show "Save & exit" only on steps where the action actually saves something
  const _saveExit = document.getElementById("wiz-save-exit");
  if (_saveExit) {{
    const _s = WIZ_STEPS[wizCurrent];
    const _canSaveExit = _s && (_s.action === "save-location-remote" || _s.action === "save-company-sizes" || _s.action === "save-daily-target" || _s.action === "save-recency-window" || _s.action === "save-profile-chips");
    _saveExit.style.display = _canSaveExit ? "" : "none";
  }}
  document.getElementById("wiz-title").textContent = s.title;
  document.getElementById("wiz-body").innerHTML = s.body;
  document.getElementById("wiz-cta").innerHTML = s.cta;
  // Slice 2.5: prefill the location/remote form if this step is the inline form
  if (s.action === "save-location-remote") {{
    fetch(PROFILE_WORKER_URL).then(function(r){{ return r.json(); }}).then(function(d){{
      const p = (d && d.profile) || {{}};
      const locsEl = document.getElementById("wiz-locs");
      const remoteEl = document.getElementById("wiz-remote");
      if (locsEl && Array.isArray(p.preferredLocations)) locsEl.value = p.preferredLocations.join(", ");
      if (remoteEl) remoteEl.value = p.remotePreference || (p.remotePreferred ? "remote-only" : "any");
    }}).catch(function(){{}});
  }}
  let dots = "";
  for (let i = 0; i < WIZ_STEPS.length; i++) {{
    if (i < wizCurrent) dots += '<div class="dot done"></div>';
    else if (i === wizCurrent) dots += '<div class="dot active"></div>';
    else dots += '<div class="dot"></div>';
  }}
  document.getElementById("wiz-progress").innerHTML = dots;
  document.getElementById("wiz-back").style.display = wizCurrent > 0 ? "" : "none";
  const skip = document.getElementById("wiz-skip");
  if (s.skipText === null) {{ skip.style.display = "none"; }}
  else {{ skip.style.display = ""; skip.textContent = s.skipText || "Skip for now"; }}
  // Step-specific lazy loaders
  if (s.action === "save-profile-chips") {{
    setTimeout(wizLoadProfileChips, 50);
  }}
}}
function wizAdvance() {{
  wizCurrent++;
  if (wizCurrent >= WIZ_STEPS.length) {{ wizFinish(); return; }}
  wizRender();
}}
function wizBack() {{ if (wizCurrent > 0) {{ wizCurrent--; wizRender(); }} }}
async function wizFinish() {{
  try {{ localStorage.setItem("gmj_wizard_seen_v2", "true"); }} catch(e) {{}}

  // Lock the CTA, show progress in place, run the AI regen against the
  // user's just-saved companySizePreferences, then trigger a dashboard
  // refresh. Everything visible to the user — no console required.
  const ctaBtn = document.getElementById("wiz-cta");
  const titleEl = document.getElementById("wiz-title");
  const bodyEl = document.getElementById("wiz-body");
  const origCtaText = ctaBtn ? ctaBtn.textContent : "";
  if (ctaBtn) {{ ctaBtn.disabled = true; ctaBtn.textContent = "Personalizing\u2026"; }}
  if (titleEl) titleEl.textContent = "Personalizing your job feed\u2026";
  if (bodyEl) bodyEl.innerHTML = '<p style="margin-bottom:8px;">Re-running the AI matcher with your latest preferences. This takes about 30\u201360 seconds.</p><p style="font-size:13px;color:#666;" id="wiz-finish-status">Calling the AI\u2026</p>';

  const statusEl = document.getElementById("wiz-finish-status");
  const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));

  let regenOk = false;
  let regenTc = 0;
  if (editKey) {{
    try {{
      const r = await fetch(WORKER_BASE + "/regenerate-profile" + USER_QS, {{
        method: "POST",
        headers: {{ "X-Edit-Key": editKey }}
      }});
      const data = await r.json().catch(function(){{ return {{}}; }});
      if (r.ok && data && data.profile) {{
        regenOk = true;
        regenTc = (data.profile.targetCompanies || []).length;
        if (statusEl) statusEl.textContent = "Generated " + regenTc + " personalized target companies. Triggering job refresh\u2026";
      }} else if (statusEl) {{
        statusEl.textContent = "Couldn\u2019t regenerate (" + ((data && data.error) || ("HTTP " + r.status)) + ") \u2014 your existing AI matches still apply.";
      }}
    }} catch (e) {{
      if (statusEl) statusEl.textContent = "Network error during regen \u2014 your existing AI matches still apply.";
    }}
  }} else if (statusEl) {{
    statusEl.textContent = "No edit key in this browser \u2014 skipping regen. (Use the invite link with ?key=\u2026 once.)";
  }}

  // Kick the GitHub Action that rebuilds dashboards regardless of regen result
  try {{ fetch(WORKER_BASE + "/refresh", {{ method: "POST" }}).catch(function(){{}}); }} catch (e) {{}}

  // Final summary then close
  if (bodyEl) {{
    const summary = regenOk
      ? "Your job feed is rebuilding now (2\u20133 min). When it\u2019s done you\u2019ll see new role suggestions tuned to your sizes and locations."
      : "Your job feed is rebuilding now (2\u20133 min). Refresh this page in a few minutes to see updates.";
    bodyEl.innerHTML = '<p style="margin-bottom:8px;color:#0a6b3a;font-weight:600;">All set!</p><p>' + summary + '</p>';
  }}
  if (titleEl) titleEl.textContent = regenOk ? ("Personalized " + regenTc + " target companies") : "Your job feed is rebuilding";
  if (ctaBtn) {{ ctaBtn.disabled = false; ctaBtn.textContent = "Close"; ctaBtn.onclick = function(){{ wizHide(); }}; }}
}}
function wizSkipPermanent() {{
  try {{ localStorage.setItem("gmj_wizard_seen_v2", "true"); }} catch(e) {{}}
  wizHide();
}}
function wizBanner(msg) {{
  const b = document.createElement("div");
  b.className = "wiz-banner";
  b.textContent = msg;
  document.body.appendChild(b);
  setTimeout(function(){{ if (b.parentNode) b.parentNode.removeChild(b); }}, 8000);
}}
function replayTour() {{ wizCurrent = 0; wizShow(); }}

// --- Wizard inline chip editor (Industries / Keywords / Specialties) -----
const WIZ_CHIP_FIELDS = ["targetTitles", "industries", "keywords", "specialties"];
let _wizChipState = {{ industries: [], keywords: [], specialties: [] }};
let _wizChipLoaded = false;

function _renderWizChipsFor(field) {{
  const cont = document.getElementById("wiz-chips-" + field);
  if (!cont) return;
  const items = _wizChipState[field] || [];
  cont.innerHTML = items.map(function(s, i) {{
    const safe = (s || "").replace(/[&<>"]/g, c => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }}[c]));
    return '<span style="display:inline-flex;align-items:center;background:#eef0ff;color:#5C5CD6;padding:3px 4px 3px 9px;border-radius:12px;font-size:11.5px;margin:2px 4px 2px 0;font-weight:500;">' + safe + '<button type="button" data-idx="' + i + '" data-field="' + field + '" class="wiz-chip-remove" style="background:none;border:0;color:#888;cursor:pointer;padding:0 0 0 6px;font-size:14px;line-height:1;font-weight:600;" title="Remove">\u00d7</button></span>';
  }}).join("");
  // Wire up the remove buttons
  cont.querySelectorAll(".wiz-chip-remove").forEach(function(btn) {{
    btn.addEventListener("click", function() {{
      const f = btn.getAttribute("data-field");
      const i = parseInt(btn.getAttribute("data-idx"), 10);
      _wizChipState[f].splice(i, 1);
      _renderWizChipsFor(f);
    }});
  }});
}}

async function wizLoadProfileChips() {{
  const statusEl = document.getElementById("wiz-chip-status");
  try {{
    const r = await fetch(WORKER_BASE + "/skills-profile" + USER_QS);
    const data = await r.json().catch(function() {{ return {{}}; }});
    const profile = (data && data.profile) || {{}};
    WIZ_CHIP_FIELDS.forEach(function(f) {{
      _wizChipState[f] = (profile[f] || []).slice();
    }});
    _wizChipLoaded = true;
    WIZ_CHIP_FIELDS.forEach(_renderWizChipsFor);
    if (statusEl) statusEl.textContent = "";
    // Wire add-input listeners (Enter to add)
    document.querySelectorAll(".wiz-chip-input").forEach(function(inp) {{
      inp.addEventListener("keydown", function(e) {{
        if (e.key !== "Enter") return;
        e.preventDefault();
        const v = inp.value.trim().toLowerCase();
        if (!v) return;
        const f = inp.getAttribute("data-target");
        if (!_wizChipState[f].includes(v)) {{
          _wizChipState[f].push(v);
          _renderWizChipsFor(f);
        }}
        inp.value = "";
      }});
    }});
  }} catch (e) {{
    if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Couldn\'t load your profile \u2014 you can still skip this step."; }}
  }}
}}

// --- Daily apply target + progress widget -----------------------------
const DAILY_TARGET_KEY = "htj_daily_apply_target_" + USER_SLUG;
function _isoToday() {{ return new Date().toISOString().slice(0, 10); }}
function refreshDailyGoalWidget() {{
  try {{
    const target = loadDailyApplyTarget();
    const today = _isoToday();
    const tracker = (typeof getTracker === "function") ? getTracker() : {{}};
    // Count tracker entries that have status set to applied/phonescreen/onsite/offer
    // AND were set today
    let todayCount = 0;
    let appliedDates = [];
    Object.values(tracker || {{}}).forEach(function(r) {{
      const st = (r && r.status) || "";
      if (!st || st === "rejected") return;
      const when = (r.statusChangedAt || r.appliedAt || r.updatedAt || r.created_at || "");
      const day = (when || "").slice(0, 10);
      if (day) appliedDates.push(day);
      if (day === today) todayCount += 1;
    }});
    const countEl = document.getElementById("goal-today-count");
    const targEl = document.getElementById("goal-today-target");
    const fillEl = document.getElementById("goal-progress-fill");
    const streakEl = document.getElementById("goal-streak");
    if (countEl) countEl.textContent = todayCount;
    if (targEl) targEl.textContent = target;
    if (fillEl) fillEl.style.width = Math.min(100, Math.round(todayCount * 100 / Math.max(1, target))) + "%";
    if (streakEl) {{
      // Count days in a row (going backwards from today) that hit target
      const byDay = {{}};
      appliedDates.forEach(d => {{ byDay[d] = (byDay[d] || 0) + 1; }});
      let streak = 0;
      let cur = new Date();
      for (let i = 0; i < 30; i++) {{
        const d = cur.toISOString().slice(0, 10);
        if ((byDay[d] || 0) >= target) {{ streak += 1; cur.setDate(cur.getDate() - 1); }}
        else break;
      }}
      streakEl.textContent = streak > 0 ? "\ud83d\udd25 " + streak + "-day streak" : "";
    }}
  }} catch (e) {{ /* swallow */ }}
}}
function wizPickDailyTarget(n) {{
  const input = document.getElementById("wiz-daily-target");
  if (input) input.value = n;
}}
function loadDailyApplyTarget() {{
  try {{ const n = parseInt(localStorage.getItem(DAILY_TARGET_KEY) || "5", 10); return (n > 0 && n < 100) ? n : 5; }} catch (e) {{ return 5; }}
}}
// --- Hiring-role detection in LinkedIn contacts -----------------------
// A contact whose Position contains words like "recruiter", "talent",
// "hiring", "people ops", "VP HR" is a higher-priority warm intro than
// a random colleague — that's literally their job.
const HIRING_ROLE_KEYWORDS = [
  "recruiter", "recruiting", "sourcer", "sourcing",
  "talent acquisition", "ta partner", "ta specialist", "ta lead",
  "hiring", "people partner", "people ops", "people operations",
  "hr business partner", "hrbp", "head of hr", "vp hr", "vp of hr",
  "vp people", "chief people", "chief talent", "chro",
  "head of people", "head of talent", "head of recruiting"
];
function _isHiringRoleContact(c) {{
  const pos = ((c && (c.position || c.title)) || "").toLowerCase();
  if (!pos) return false;
  return HIRING_ROLE_KEYWORDS.some(k => pos.indexOf(k) !== -1);
}}


// --- Auth recovery modal ----------------------------------------------
// Surfaced whenever an auth-required action returns 401. Lets the user
// (a) paste a fresh invite URL OR (b) email Amit to resend one.
const ADMIN_EMAIL = "amittarora@gmail.com";

function recoveryShow() {{
  const o = document.getElementById("recovery-modal");
  if (!o) return;
  // Build the mailto link with prefilled subject/body
  const subj = encodeURIComponent("Please resend my invite link to getmemyjob");
  const body = encodeURIComponent(
    "Hi Amit,\\n\\n" +
    "My access key to my getmemyjob dashboard isn\'t working anymore. " +
    "Could you please resend a fresh invite link?\\n\\n" +
    "User slug: " + USER_SLUG + "\\n" +
    "Dashboard: " + window.location.origin + "/" + USER_SLUG + ".html\\n\\n" +
    "Thanks!"
  );
  const a = document.getElementById("recovery-mailto");
  if (a) a.href = "mailto:" + ADMIN_EMAIL + "?subject=" + subj + "&body=" + body;
  const status = document.getElementById("recovery-paste-status");
  if (status) {{ status.textContent = ""; status.className = "recovery-status"; }}
  o.classList.add("show");
}}
function recoveryHide() {{
  const o = document.getElementById("recovery-modal");
  if (o) o.classList.remove("show");
}}
function recoveryApplyPaste() {{
  const input = document.getElementById("recovery-paste-input");
  const status = document.getElementById("recovery-paste-status");
  if (!input || !status) return;
  const raw = (input.value || "").trim();
  if (!raw) {{
    status.className = "recovery-status err";
    status.textContent = "Paste your full invite URL here first.";
    return;
  }}
  // Extract ?key=... from the URL
  let key = null;
  try {{
    const u = new URL(raw);
    key = u.searchParams.get("key");
    // If the URL is for a different user, warn (but still store the key)
    const path = u.pathname.replace(/^\/+/, "").replace(/\.html$/, "");
    if (path && path !== USER_SLUG) {{
      status.className = "recovery-status err";
      status.textContent = "That URL is for user '" + path + "', not '" + USER_SLUG + "'. Open the right dashboard URL first.";
      return;
    }}
  }} catch (e) {{
    // Maybe they just pasted the key itself
    if (/^[a-zA-Z0-9_-]{{6,}}$/.test(raw)) key = raw;
  }}
  if (!key) {{
    status.className = "recovery-status err";
    status.textContent = "Couldn\'t find a ?key=... in that URL. Try the full invite link.";
    return;
  }}
  // Stash both per-user and legacy keys
  try {{
    localStorage.setItem("htj_resume_key_" + USER_SLUG, key);
    localStorage.setItem("htj_resume_key", key);
  }} catch (e) {{}}
  status.className = "recovery-status ok";
  status.textContent = "Saved. Retrying\u2026";
  // Auto-close and trigger a regen retry
  setTimeout(function() {{
    recoveryHide();
    const btn = document.getElementById("regen-btn");
    if (btn && typeof regenerateFromHeader === "function") regenerateFromHeader(btn);
  }}, 700);
}}


// Header "Regenerate matches" button — fires /regenerate-profile with
// whichever auth header the browser has cached. Tries X-Edit-Key first
// (per-user, from invite link). Falls back to X-Admin-Key (from admin.html)
// if the edit key is missing or rejected as invalid.
async function regenerateFromHeader(btn) {{
  const orig = btn.textContent;
  const editKey = (typeof getEditKey === "function")
    ? getEditKey()
    : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
  const adminKey = localStorage.getItem("htj_admin_key");
  // Build attempts in order of preference
  const attempts = [];
  if (editKey) attempts.push({{ header: "X-Edit-Key", value: editKey, label: "edit key" }});
  if (adminKey) attempts.push({{ header: "X-Admin-Key", value: adminKey, label: "admin key" }});
  if (attempts.length === 0) {{
    wizBanner("Can't regenerate \u2014 no auth in this browser. Either re-open your invite link with ?key=\u2026, or open admin.html and sign in once first.");
    return;
  }}
  btn.disabled = true;
  btn.textContent = "Regenerating\u2026";
  wizBanner("Re-running the AI matcher with your latest preferences. Takes about 30\u201360 seconds.");
  let lastErr = "";
  for (let i = 0; i < attempts.length; i++) {{
    const a = attempts[i];
    try {{
      const r = await fetch(WORKER_BASE + "/regenerate-profile" + USER_QS, {{
        method: "POST",
        headers: {{ [a.header]: a.value }}
      }});
      const data = await r.json().catch(function() {{ return {{}}; }});
      if (r.ok && !(data && data.error)) {{
        const tcCount = ((data.profile || {{}}).targetCompanies || []).length;
        wizBanner("Generated " + tcCount + " personalized target companies via " + a.label + ". Triggering job refresh\u2026");
        try {{ fetch(WORKER_BASE + "/refresh", {{ method: "POST" }}); }} catch (e) {{}}
        btn.textContent = "Refreshing\u2026 (reload in 2\u20133 min)";
        btn.disabled = false;
        setTimeout(function() {{ btn.textContent = orig; }}, 12000);
        return;
      }}
      lastErr = (data && data.error) || ("HTTP " + r.status);
      // 401 → try the next auth method; other codes → give up
      if (r.status !== 401) break;
    }} catch (e) {{
      lastErr = "network error: " + (e.message || e);
      break;
    }}
  }}
  // If the failure looked like an auth problem, pop the recovery modal
  // instead of just a banner. Otherwise show the banner as before.
  if (/Invalid X-Edit-Key|Invalid X-Admin-Key|HTTP 401/.test(lastErr)) {{
    btn.textContent = orig;
    btn.disabled = false;
    recoveryShow();
    return;
  }}
  wizBanner("Regen failed: " + lastErr);
  btn.textContent = orig;
  btn.disabled = false;
}}


// --- Wizard step 5: company-size mix sliders ---------------------------
// Drag any slider; the other two auto-adjust proportionally so the
// total stays at 100. Same when a number input is typed.
function _wizMixRebalance(changedKey) {{
  const keys = ["startup", "midsize", "large"];
  const vals = {{}};
  keys.forEach(function(k) {{
    const el = document.getElementById("wiz-mix-" + k);
    vals[k] = Math.max(0, Math.min(100, parseInt(el.value, 10) || 0));
  }});
  const others = keys.filter(function(k) {{ return k !== changedKey; }});
  const remaining = 100 - vals[changedKey];
  if (remaining <= 0) {{
    vals[changedKey] = 100;
    others.forEach(function(k) {{ vals[k] = 0; }});
  }} else {{
    const otherSum = vals[others[0]] + vals[others[1]];
    if (otherSum === 0) {{
      const half = Math.floor(remaining / 2);
      vals[others[0]] = half;
      vals[others[1]] = remaining - half;
    }} else {{
      vals[others[0]] = Math.round(vals[others[0]] / otherSum * remaining);
      vals[others[1]] = remaining - vals[others[0]];
    }}
  }}
  keys.forEach(function(k) {{
    const slider = document.getElementById("wiz-mix-" + k);
    const num = document.getElementById("wiz-mix-" + k + "-num");
    if (slider) slider.value = vals[k];
    if (num) num.value = vals[k];
  }});
  const sumEl = document.getElementById("wiz-mix-sum-val");
  if (sumEl) sumEl.textContent = vals.startup + vals.midsize + vals.large;
}}
function wizMixOnSlide(key) {{ _wizMixRebalance(key); }}
function wizMixOnNum(key) {{
  const num = document.getElementById("wiz-mix-" + key + "-num");
  const slider = document.getElementById("wiz-mix-" + key);
  if (num && slider) slider.value = num.value;
  _wizMixRebalance(key);
}}

(function wizardSetup() {{
  function setup() {{
    const cta = document.getElementById("wiz-cta");
    const back = document.getElementById("wiz-back");
    const skip = document.getElementById("wiz-skip");
    if (!cta || !back || !skip) return;

    cta.addEventListener("click", function() {{
      const s = WIZ_STEPS[wizCurrent];
      if (s.action === "next") {{ wizAdvance(); return; }}
      if (s.action === "open-resume") {{
        wizHide();
        try {{ openResumeModal(); }} catch(e) {{ console.error(e); }}
        window._wizExpect = "resume";
        return;
      }}
      if (s.action === "open-resume-profile") {{
        wizHide();
        try {{ openResumeModal(); }} catch(e) {{ console.error(e); }}
        setTimeout(function() {{
          const tabs = document.querySelectorAll(".tab-btn");
          for (let i = 0; i < tabs.length; i++) {{
            if (tabs[i].textContent.toLowerCase().indexOf("profile") !== -1) {{ tabs[i].click(); break; }}
          }}
        }}, 300);
        window._wizExpect = "profile";
        return;
      }}
      if (s.action === "open-contacts") {{
        wizHide();
        try {{ openContactsModal(); }} catch(e) {{ console.error(e); }}
        window._wizExpect = "contacts";
        return;
      }}
      if (s.action === "save-location-remote") {{
        const locsInput = document.getElementById("wiz-locs");
        const remoteSel = document.getElementById("wiz-remote");
        const statusEl = document.getElementById("wiz-locs-status");
        if (!locsInput || !remoteSel) {{ wizAdvance(); return; }}
        const locs = locsInput.value.split(",").map(function(x){{ return x.trim(); }}).filter(Boolean);
        const remotePref = remoteSel.value || "any";
        if (statusEl) statusEl.textContent = "Saving\u2026";
        const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
        if (!editKey) {{
          if (statusEl) statusEl.textContent = "No edit key found \u2014 your changes can't be saved. Skipping.";
          setTimeout(wizAdvance, 1200);
          return;
        }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: Object.assign({{ "Content-Type": "application/json" }}, authHeader),
          body: JSON.stringify({{ patchFields: {{ preferredLocations: locs, remotePreference: remotePref }} }})
        }})
          .then(function(r){{ return r.json().then(function(d){{ return {{ ok: r.ok, status: r.status, data: d }}; }}); }})
          .then(function(res){{
            if (!res.ok || (res.data && res.data.error)) {{
              if (statusEl) statusEl.textContent = "Save failed (" + (res.data.error || ("HTTP " + res.status)) + ") \u2014 continuing anyway.";
              setTimeout(wizAdvance, 1500);
            }} else {{
              if (statusEl) statusEl.textContent = "Saved.";
              setTimeout(function(){{
                if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
                else {{ wizAdvance(); }}
              }}, 400);
            }}
          }})
          .catch(function(e){{
            if (statusEl) statusEl.textContent = "Network error \u2014 continuing anyway.";
            setTimeout(function(){{
              if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
              else {{ wizAdvance(); }}
            }}, 1200);
          }})
          .finally(function(){{ if (ctaBtn) ctaBtn.disabled = false; }});
        return;
      }}
      if (s.action === "save-company-sizes") {{
        const statusEl = document.getElementById("wiz-mix-msg");
        function _readVal(k) {{
          const el = document.getElementById("wiz-mix-" + k);
          return Math.max(0, Math.min(100, parseInt(el ? el.value : 0, 10) || 0));
        }}
        const mix = {{
          startup: _readVal("startup"),
          midsize: _readVal("midsize"),
          large: _readVal("large")
        }};
        const total = mix.startup + mix.midsize + mix.large;
        if (total !== 100) {{
          // Normalize so sum == 100 (rounding-safe)
          if (total === 0) {{ mix.startup = 33; mix.midsize = 33; mix.large = 34; }}
          else {{
            mix.startup = Math.round(mix.startup * 100 / total);
            mix.midsize = Math.round(mix.midsize * 100 / total);
            mix.large = 100 - mix.startup - mix.midsize;
          }}
        }}
        const derivedPrefs = ["startup","midsize","large"].filter(function(k){{ return mix[k] > 0; }});
        if (statusEl) {{ statusEl.style.color = "#888"; statusEl.textContent = "Saving\u2026"; }}
        const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
        if (!editKey) {{
          if (statusEl) statusEl.textContent = "No edit key in this browser \u2014 your choice can't be saved. Skipping.";
          setTimeout(wizAdvance, 1200);
          return;
        }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{ companySizeMix: mix, companySizePreferences: derivedPrefs }} }})
        }})
          .then(function(r){{ return r.json().then(function(d){{ return {{ ok: r.ok, status: r.status, data: d }}; }}); }})
          .then(function(res){{
            if (!res.ok || (res.data && res.data.error)) {{
              if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Save failed (" + (res.data.error || ("HTTP " + res.status)) + ") \u2014 continuing."; }}
              setTimeout(wizAdvance, 1500);
            }} else {{
              if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved: " + mix.startup + "/" + mix.midsize + "/" + mix.large + " (startup/mid/large)."; }}
              setTimeout(function(){{
                if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
                else {{ wizAdvance(); }}
              }}, 600);
            }}
          }})
          .catch(function(e){{
            if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Network error \u2014 continuing."; }}
            setTimeout(function(){{
              if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
              else {{ wizAdvance(); }}
            }}, 1200);
          }})
          .finally(function(){{ if (ctaBtn) ctaBtn.disabled = false; }});
        return;
      }}
      if (s.action === "save-profile-chips") {{
        const statusEl = document.getElementById("wiz-chip-save-status");
        if (!_wizChipLoaded) {{ if (statusEl) statusEl.textContent = "Profile didn\'t load \u2014 skipping."; setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 800); return; }}
        let editKey = (typeof getEditKey === "function") ? getEditKey() : null;
        const adminKey = localStorage.getItem("htj_admin_key");
        const authHeader = editKey ? {{ "X-Edit-Key": editKey }} : (adminKey ? {{ "X-Admin-Key": adminKey }} : null);
        if (!authHeader) {{
          if (statusEl) statusEl.textContent = "Session expired \u2014 click Confirm to verify.";
          if (typeof showVerifyModal === "function") showVerifyModal(function() {{ wizAdvance(); }});
          return;
        }}
        if (statusEl) {{ statusEl.style.color = "#888"; statusEl.textContent = "Saving\u2026"; }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{
            targetTitles: _wizChipState.targetTitles,
            industries: _wizChipState.industries,
            keywords: _wizChipState.keywords,
            specialties: _wizChipState.specialties,
          }} }})
        }})
          .then(function(r) {{ return r.json().then(function(d) {{ return {{ ok: r.ok, status: r.status, data: d }}; }}); }})
          .then(function(res) {{
            if (!res.ok || (res.data && res.data.error)) {{
              if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Save failed (" + (res.data.error || ("HTTP " + res.status)) + ") \u2014 continuing."; }}
              setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 1500);
            }} else {{
              if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved \u2014 " + (_wizChipState.industries.length + _wizChipState.keywords.length + _wizChipState.specialties.length) + " signals."; }}
              setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 600);
            }}
          }})
          .catch(function() {{
            if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Network error \u2014 continuing."; }}
            setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 1200);
          }})
          .finally(function() {{ if (ctaBtn) ctaBtn.disabled = false; }});
        return;
      }}
      if (s.action === "save-recency-window") {{
        const picked = document.querySelector('input[name="wiz-recency"]:checked');
        const val = picked ? picked.value : "7";
        const statusEl = document.getElementById("wiz-recency-status");
        try {{ localStorage.setItem(RECENCY_WINDOW_KEY, val); }} catch (e) {{}}
        try {{ pushPrefToProfile("recencyWindow", String(val)); }} catch (e) {{}}
        // Also apply immediately if the user is viewing the dashboard
        try {{
          activeWindow = String(val);
          _restoreRecencyWindow();
        }} catch (e) {{}}
        if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved: " + (val === "0" ? "Last 24 hours" : val === "all" ? "All jobs" : "Last " + val + " days"); }}
        setTimeout(function() {{
          if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
          else {{ wizAdvance(); }}
        }}, 500);
        return;
      }}
      if (s.action === "save-daily-target") {{
        const input = document.getElementById("wiz-daily-target");
        const statusEl = document.getElementById("wiz-daily-status");
        let n = parseInt(input ? input.value : "5", 10);
        if (isNaN(n) || n < 1) n = 5;
        if (n > 50) n = 50;
        try {{ localStorage.setItem(DAILY_TARGET_KEY, String(n)); }} catch (e) {{}}
        try {{ pushPrefToProfile("dailyTarget", n); }} catch (e) {{}}
        if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved: " + n + "/day"; }}
        setTimeout(function() {{
          if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
          else {{ wizAdvance(); }}
        }}, 500);
        return;
      }}
      if (s.action === "finish") {{ wizFinish(); return; }}
    }});
    back.addEventListener("click", wizBack);
    skip.addEventListener("click", function() {{
      const s = WIZ_STEPS[wizCurrent];
      if (s.action && s.action !== "next" && s.action !== "finish") {{ wizAdvance(); return; }}
      wizSkipPermanent();
    }});
    const saveExitBtn = document.getElementById("wiz-save-exit");
    if (saveExitBtn) {{
      saveExitBtn.addEventListener("click", function() {{
        // Set a flag the save handlers honor: after a successful save, exit
        // the wizard (run regen + close) instead of advancing to the next step.
        window._wizExitAfterSave = true;
        cta.click();
      }});
    }}

    // Wrap existing close handlers so the wizard resumes after a modal closes
    if (typeof closeResumeModal === "function") {{
      const _origCloseResume = closeResumeModal;
      window.closeResumeModal = function() {{
        _origCloseResume.apply(this, arguments);
        if (window._wizExpect === "resume" || window._wizExpect === "profile") {{
          window._wizExpect = null;
          wizAdvance();
          setTimeout(wizShow, 180);
        }}
      }};
    }}
    if (typeof closeContactsModal === "function") {{
      const _origCloseContacts = closeContactsModal;
      window.closeContactsModal = function() {{
        _origCloseContacts.apply(this, arguments);
        if (window._wizExpect === "contacts") {{
          window._wizExpect = null;
          wizAdvance();
          setTimeout(wizShow, 180);
        }}
      }};
    }}

    // Auto-launch when this version of the wizard hasn't been seen yet.
    // Note: dropped the !HAS_PROFILE_AT_RENDER guard so existing users
    // also get prompted when we bump the wizard flag (e.g. to ask new
    // questions like company-size preference). Users can skip steps
    // that aren't relevant (resume upload, etc.).
    try {{
      const seen = localStorage.getItem("gmj_wizard_seen_v2");
      if (!seen) {{ setTimeout(wizShow, 450); }}
    }} catch(e) {{}}
  }}
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", setup);
  }} else {{
    setup();
  }}
}})();
</script>
</body></html>"""


if __name__ == "__main__":
    run()
